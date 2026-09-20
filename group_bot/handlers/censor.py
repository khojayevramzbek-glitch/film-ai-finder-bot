import asyncio
import re
from datetime import datetime, timezone, timedelta
from html import escape
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest

try:
    from group_bot.database import (
        is_censor_enabled,
        set_censor_status,
        add_custom_bad_word,
        remove_custom_bad_word,
        get_custom_bad_words,
    )
except ImportError:
    from database import (
        is_censor_enabled,
        set_censor_status,
        add_custom_bad_word,
        remove_custom_bad_word,
        get_custom_bad_words,
    )

router = Router()

# -------------------------------------------------------------
# 1. Normalizatsiya va harflarni almashtirish (Anti-Bypass)
# -------------------------------------------------------------
CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '',
    'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'ya': 'ya'
}

LEET_REPLACEMENTS = {
    '@': 'a', '0': 'o', '1': 'i', '3': 'e', '$': 's', '!': 'i',
    '7': 't', '4': 'a', '5': 's', '8': 'b', '<': 'c'
}

# -------------------------------------------------------------
# 2. Taqiqlangan so'zlar bazasi (O'zbekcha, Ruscha, Inglizcha)
# -------------------------------------------------------------

# O'zbekcha haqorat va so'kinishlar
UZBEK_BAD_PATTERNS = [
    r'\b(onang[nd]i|enang[nd]i|opang[nd]i|singling[nd]i|oting[nd]i|otang[nd]i)\b',
    r'\b(itvachcha|xaromi|haromi|jalap|jalaq|gandon|foxisha|fohisha|qanjiq|dalbayob|padariga|amxona|omxona|qotoq|qoxtoq|kutvachcha)\b',
    r'\b(siktir[a-z]*|sikvotti|sikaman|sikay|sikarman|sikyatgan|sikish)\b',
    r'\b(s[i1]k[i1]sh|s[i1]k[a-z]+)\b',
    r'\b(am|om)(i|[nd]i|ing|ingni|ingi|xona|xo[\'`]?r|taloq)\b',
    r'\b(ami|omini|omingni|amingni)\b',
    r'\b(ko[\'`]?t|kot)(i|[nd]i|[nd]a|[nd]an|[nd]iki|ing|ingni|inga|vachcha)\b',
    r'\b(ko[\'`]?tsan|kotsan)\b',
]

# Ruscha matlar (Kirill va Translit)
RUSSIAN_BAD_PATTERNS = [
    r'(?i)\b(ху[йиеяё][а-я]*|хули|хер[а-я]*|пизд[а-я]*|еб[а-яё]*|ёб[а-яё]*|бля[тд][а-я]*|сук[а-я]*|сучк[а-я]*|муда[кч][а-я]*|пид[ao]р[а-я]*|гандон[а-я]*|гондон[а-я]*|шлюх[а-я]*|залуп[а-я]*|дроч[а-я]*)\b',
    r'\b(xuy[a-z]*|huy[a-z]*|pizd[a-z]*|yeb[a-z]*|eb[a-z]*|blya[td][a-z]*|suk[ai][a-z]*|mudak[a-z]*|pid[ao]r[a-z]*|shlyux[a-z]*|gandon[a-z]*|chmo)\b',
]

# Inglizcha haqoratlar
ENGLISH_BAD_PATTERNS = [
    r'\b(fuck[a-z]*|bitch[a-z]*|cunt[a-z]*|asshole[a-z]*|dick[a-z]*|pussy[a-z]*|bastard[a-z]*|whore[a-z]*|slut[a-z]*|motherfuck[a-z]*)\b',
    r'\b(shit|faggot)\b',
]

# Barcha standart naqshlarni birlashtirish
ALL_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (UZBEK_BAD_PATTERNS + RUSSIAN_BAD_PATTERNS + ENGLISH_BAD_PATTERNS)
]

# Ruxsat berilgan oddiy so'zlar (False Positive bo'lmasligi uchun)
EXCLUDED_SAFE_WORDS = {
    'kutubxona', 'kutish', 'kutib', 'komanda', 'rubl', 'salom', 'tamom',
    'katta', 'sikl', 'tsikl', 'sirk', 'kuti', 'kutgani', 'kutaylik'
}


def normalize_text(text: str) -> str:
    """
    Matnni har xil hiylalardan tozalash:
    - Kichik harfga o'tkazish
    - Belgilar va raqamlarni harfga aylantirish (@ -> a, 0 -> o)
    - Kirillni lotinga o'tkazish
    - Harflar orasidagi nuqta, probel, yulduzchalarni olib tashlash
    """
    if not text:
        return ""

    result = text.lower()

    # 1. Leetspeak almashtirish
    for char, rep in LEET_REPLACEMENTS.items():
        result = result.replace(char, rep)

    # 2. Kirillni lotinga almashtirish
    for char, rep in CYRILLIC_TO_LATIN.items():
        result = result.replace(char, rep)

    return result


def is_profane(text: str, custom_words: list[str] = None) -> bool:
    """
    Matnda haqorat yoki so'kinish borligini tekshiradi.
    """
    if not text or not text.strip():
        return False

    raw_lower = text.lower()
    normalized = normalize_text(text)

    # A) Xabar ichidagi bo'lak so'zlarni tekshirish
    words = re.findall(r'[a-zA-Zа-яА-ЯёЁ]+', raw_lower)
    norm_words = re.findall(r'[a-zA-Z]+', normalized)

    # Harflar orasida probel yoki nuqtalar bo'lsa (masalan: s.u.k.a yoki s u k a)
    condensed = re.sub(r'[\s\.\,\*\-\_\~\#\/\\]+', '', normalized)

    # 1. Standart naqshlar bo'yicha tekshirish
    for pattern in ALL_PATTERNS:
        if pattern.search(raw_lower) or pattern.search(normalized):
            # Safe words tekshiruvi
            matched_words = [w for w in words if w in EXCLUDED_SAFE_WORDS]
            if not matched_words:
                return True

        # Qisqartirilgan/birlashgan shaklda tekshirish (masalan s.u.k.a)
        if pattern.search(condensed):
            return True

    # 2. Guruh uchun maxsus kiritilgan taqiqlangan so'zlar
    if custom_words:
        for cw in custom_words:
            cw_norm = normalize_text(cw)
            if cw_norm in normalized or cw_norm in condensed or cw in raw_lower:
                return True

    return False


async def is_telegram_admin(chat_id: int, user_id: int, bot: Bot) -> bool:
    """Foydalanuvchi guruh admini yoki egasi ekanligini aniqlash."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


async def delete_message_later(bot: Bot, chat_id: int, message_id: int, delay: int = 15):
    """Xabarni ma'lum vaqtdan so'ng chatdan avtomatik tozalash."""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


# -------------------------------------------------------------
# 3. Admin Buyruqlari (/censor on/off, /addbadword, /delbadword)
# -------------------------------------------------------------

@router.message(Command("censor"))
async def cmd_censor(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        if message.chat.type == ChatType.PRIVATE:
            await message.reply(
                "ℹ️ <b>So'kinish filtri (Censor) guruhlar uchun mo'ljallangan!</b>\n\n"
                "1. Botni guruhingizga qo'shing va <b>Admin</b> huquqini bering.\n"
                "2. Guruh ichida <code>/censor on</code> yoki <code>/censor off</code> deb yozing.",
                parse_mode="HTML"
            )
        return

    if not await is_telegram_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = is_censor_enabled(message.chat.id)
        status_text = "🟢 Yoqilgan" if current else "🔴 O'chirilgan"
        await message.reply(
            f"ℹ️ <b>So'kinish va Haqorat Filtri (Censor):</b> {status_text}\n\n"
            f"O'zgartirish uchun:\n"
            f"• <code>/censor on</code> — Filtrni yoqish\n"
            f"• <code>/censor off</code> — Filtrni o'chirish",
            parse_mode="HTML"
        )
        return

    action = args[1].strip().lower()
    if action == "on":
        set_censor_status(message.chat.id, True)
        await message.reply("✅ <b>So'kinish va haqorat filtri YOQILDI!</b>\n<i>Guruh tozaligi nazorat ostida.</i>", parse_mode="HTML")
    elif action == "off":
        set_censor_status(message.chat.id, False)
        await message.reply("⚠️ <b>So'kinish va haqorat filtri O'CHIRILDI.</b>", parse_mode="HTML")
    else:
        await message.reply("❗ Noto'g'ri buyruq. <code>/censor on</code> yoki <code>/censor off</code> deb yozing.", parse_mode="HTML")


@router.message(Command("addbadword"))
async def cmd_addbadword(message: types.Message, bot: Bot):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply("❗ Foydalanish: <code>/addbadword &lt;taqiqlangan so'z&gt;</code>\nMasalan: <code>/addbadword ahmoq</code>", parse_mode="HTML")
        return

    word = args[1].strip().strip("<>\"' ").lower()
    if not word:
        await message.reply("❗ Iltimos, haqiqiy so'z kiriting!", parse_mode="HTML")
        return

    # Lichkada (shaxsiy chatda)
    if message.chat.type == ChatType.PRIVATE:
        add_custom_bad_word(0, word)
        if is_profane(word):
            await message.reply(
                f"✅ <b>'{escape(word)}'</b> taqiqlangan so'zlar ro'yxatiga qo'shildi!\n\n"
                f"💡 <i>Eslatma: Bu so'z allaqachon botning standart bazasida ham mavjud va guruhlarda avtomatik bloklanadi.</i>",
                parse_mode="HTML"
            )
        else:
            await message.reply(
                f"✅ <b>'{escape(word)}'</b> muvaffaqiyatli taqiqlangan so'zlar ro'yxatiga qo'shildi!\n\n"
                f"Endi bot ushbu so'zni barcha guruhlarda avtomatik tarzda o'chiradi va yozgan foydalanuvchiga 1 daqiqa mute beradi.",
                parse_mode="HTML"
            )
        return

    if message.chat.type == ChatType.CHANNEL:
        return

    # Guruhda
    if not await is_telegram_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    add_custom_bad_word(message.chat.id, word)
    await message.reply(f"✅ <b>'{escape(word)}'</b> so'zi guruhning qora ro'yxatiga qo'shildi.", parse_mode="HTML")


@router.message(Command("delbadword"))
async def cmd_delbadword(message: types.Message, bot: Bot):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply("❗ Foydalanish: <code>/delbadword &lt;so'z&gt;</code>", parse_mode="HTML")
        return

    word = args[1].strip().strip("<>\"' ").lower()

    # Lichkada
    if message.chat.type == ChatType.PRIVATE:
        removed = remove_custom_bad_word(0, word)
        if removed:
            await message.reply(f"✅ <b>'{escape(word)}'</b> so'zi qora ro'yxatdan o'chirildi.", parse_mode="HTML")
        else:
            await message.reply(f"ℹ️ <b>'{escape(word)}'</b> ro'yxatda topilmadi.", parse_mode="HTML")
        return

    if message.chat.type == ChatType.CHANNEL:
        return

    # Guruhda
    if not await is_telegram_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    removed = remove_custom_bad_word(message.chat.id, word)
    if removed:
        await message.reply(f"✅ <b>'{escape(word)}'</b> so'zi qora ro'yxatdan o'chirildi.", parse_mode="HTML")
    else:
        await message.reply(f"ℹ️ <b>'{escape(word)}'</b> so'zi ro'yxatda topilmadi.", parse_mode="HTML")


@router.message(Command("badwords"))
async def cmd_badwords(message: types.Message, bot: Bot):
    # Lichkada
    if message.chat.type == ChatType.PRIVATE:
        words = get_custom_bad_words(0)
        if words:
            words_list = ", ".join(f"<code>{escape(w)}</code>" for w in words)
            await message.reply(
                f"📋 <b>Qo'shilgan Maxsus Taqiqlangan So'zlar:</b>\n{words_list}\n\n"
                f"💡 <i>Bundan tashqari, botning standart bazasida yuzlab o'zbekcha, ruscha va inglizcha so'kinishlar doimiy faol!</i>",
                parse_mode="HTML"
            )
        else:
            await message.reply(
                "ℹ️ Hozircha qo'shimcha maxsus so'zlar kiritilmagan.\n\n"
                "💡 <i>Lekin botning standart bazasida 'gandon', 'xaromi' kabi yuzlab o'zbekcha, ruscha va inglizcha so'kinishlar avtomatik bloklanadi!</i>\n\n"
                "Yangi so'z qo'shish uchun: <code>/addbadword &lt;so'z&gt;</code>",
                parse_mode="HTML"
            )
        return

    if message.chat.type == ChatType.CHANNEL:
        return

    # Guruhda
    if not await is_telegram_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    words = get_custom_bad_words(message.chat.id)
    if words:
        words_list = ", ".join(f"<code>{escape(w)}</code>" for w in words)
        await message.reply(f"📋 <b>Guruhning Maxsus Taqiqlangan So'zlari:</b>\n{words_list}", parse_mode="HTML")
    else:
        await message.reply("ℹ️ Ushbu guruhda hozircha qo'shimcha taqiqlangan so'zlar yo'q. Standart filtr faol.", parse_mode="HTML")


# -------------------------------------------------------------
# 4. Asosiy Xabarlarni Tekshirish (Censor Listener)
# -------------------------------------------------------------

@router.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def check_profanity(message: types.Message, bot: Bot):
    if not message.from_user or message.from_user.is_bot:
        return

    chat_id = message.chat.id
    user = message.from_user

    # Censor filtri o'chirilgan bo'lsa tekshirmaymiz
    if not is_censor_enabled(chat_id):
        return

    text = message.text or message.caption or ""
    if not text:
        return

    custom_words = get_custom_bad_words(chat_id)
    if not is_profane(text, custom_words):
        return

    # Haqorat aniqlandi!
    # 1. Haqoratli xabarni darhol o'chirish
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    except Exception:
        pass

    is_admin = await is_telegram_admin(chat_id, user.id, bot)

    # 2. Xatti-harakat: Admin bo'lsa qat'iy ogohlantirish, oddiy foydalanuvchi bo'lsa 1 minut mute
    if is_admin:
        warn_msg = await message.answer(
            f"⚠️ <b>{escape(user.full_name)}</b>, admin bo'lib turib so'kinmang! "
            f"Iltimos, boshqalarga o'rnak bo'ling va qoidalarga rioya qiling!",
            parse_mode="HTML"
        )
        asyncio.create_task(delete_message_later(bot, chat_id, warn_msg.message_id, delay=15))
    else:
        # 1 daqiqa mute
        until_date = datetime.now(timezone.utc) + timedelta(minutes=1)
        try:
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=permissions,
                until_date=until_date
            )
            warn_msg = await message.answer(
                f"⚠️ <b>{escape(user.full_name)}</b>, guruhda so'kinish va haqorat qat'iyan taqiqlangan!\n"
                f"<i>Siz 1 daqiqaga yozishdan cheklandingiz (Mute).</i>",
                parse_mode="HTML"
            )
            asyncio.create_task(delete_message_later(bot, chat_id, warn_msg.message_id, delay=15))
        except TelegramBadRequest as e:
            pass
