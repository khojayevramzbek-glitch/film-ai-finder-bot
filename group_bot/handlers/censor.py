import asyncio
import re
from datetime import datetime, timezone, timedelta
from html import escape
from typing import Any, Callable, Dict, Awaitable

from aiogram import Router, types, Bot, BaseMiddleware
from aiogram.filters import Command
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import ChatPermissions, Message, TelegramObject
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
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '',
    'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
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
    r'\b(onang[nd]i|enang[nd]i|opang[nd]i|singling[nd]i|oting[nd]i|otang[nd]i|onangni|enangni|padaring[a-z]*)\b',
    r'\b(itvachcha|xaromi[a-z]*|haromi[a-z]*|jalap[a-z]*|jalaq[a-z]*|gandon[a-z]*|foxisha[a-z]*|fohisha[a-z]*|qanjiq[a-z]*|dalbayob[a-z]*|dalbaeb[a-z]*|amxona|omxona|kutvachcha)\b',
    r'\b(qotoq[a-z]*|qoxtoq[a-z]*)\b',
    r'\b(siktir[a-z]*|sikvotti|sikaman|sikay|sikarman|sikyatgan|sikish|sikaylik|sikaychi|sikvor)\b',
    r'\b(s[i1]k[a-z]*)\b',
    r'\b(am|om)(i|[nd]i|ing|ingni|ingi|xona|xo[\'`]?r|taloq|san|cha)\b',
    r'\b(ami|omini|omingni|amingni|amisan|omisan)\b',
    r'\b(kot|koot)(i|[nd]i|[nd]a|[nd]an|[nd]iki|ing|ingni|inga|vachcha|san|cha|lar|boz)?\b',
]

# Ruscha matlar (Kirill va Translit)
RUSSIAN_BAD_PATTERNS = [
    r'\b(xuy[a-z]*|huy[a-z]*|pizd[a-z]*|yeb[a-z]*|eb[a-z]*|blya[a-z]*|blat|suk[ai][a-z]*|mudak[a-z]*|pid[ao]r[a-z]*|shlyux[a-z]*|gandon[a-z]*|gondon[a-z]*|chmo|zaluip[a-z]*|droch[a-z]*)\b',
]

# Inglizcha haqoratlar
ENGLISH_BAD_PATTERNS = [
    r'\b(fuck[a-z]*|bitch[a-z]*|cunt[a-z]*|asshole[a-z]*|dick[a-z]*|pussy[a-z]*|bastard[a-z]*|whore[a-z]*|slut[a-z]*|motherfuck[a-z]*)\b',
    r'\b(shit|faggot)\b',
]

ALL_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (UZBEK_BAD_PATTERNS + RUSSIAN_BAD_PATTERNS + ENGLISH_BAD_PATTERNS)
]

# Ruxsat berilgan oddiy so'zlar (False Positive bo'lmasligi uchun)
EXCLUDED_SAFE_WORDS = {
    'kutubxona', 'kutish', 'kutib', 'komanda', 'rubl', 'salom', 'tamom',
    'katta', 'sikl', 'tsikl', 'sirk', 'kuti', 'kutgani', 'kutaylik',
    'rahmat', 'yaxshi', 'qanday', 'assalomu', 'alaykum', 'amal', 'omon'
}


def normalize_text(text: str) -> str:
    """Matnni leetspeak, kirill va apostroflardan tozalab kichik harfga o'tkazish."""
    if not text:
        return ""

    res = text.lower()
    for char, rep in LEET_REPLACEMENTS.items():
        res = res.replace(char, rep)

    for char, rep in CYRILLIC_TO_LATIN.items():
        res = res.replace(char, rep)

    # Apostroflarni olib tashlash (ko't -> kot, qo'toq -> qotoq)
    res = re.sub(r'[\'’`ʻ‘]', '', res)
    return res


def is_profane(text: str, custom_words: list[str] = None) -> bool:
    """Matnda haqorat yoki so'kinish borligini tekshirish."""
    if not text or not text.strip():
        return False

    normalized = normalize_text(text)
    words = re.findall(r'[a-z]+', normalized)

    # 1. So'zma-so'z tekshirish
    for w in words:
        if w in EXCLUDED_SAFE_WORDS:
            continue
        for pattern in ALL_PATTERNS:
            if pattern.search(w):
                return True
        if custom_words:
            for cw in custom_words:
                clean_cw = normalize_text(cw)
                if clean_cw and clean_cw == w:
                    return True

    # 2. Xabar ichida orasi ochiq yoki belgilar bilan yozilgan bo'lsa (masalan: s u k a, s.u.k.a, g a n d o n)
    condensed = re.sub(r'[^a-z]+', '', normalized)
    condensed_keywords = [
        'gandon', 'jalap', 'xaromi', 'haromi', 'dalbayob', 'itvachcha',
        'suka', 'blyat', 'pizda', 'xuy', 'huy', 'yebal', 'ebat',
        'fuck', 'bitch', 'asshole', 'qotoq', 'siktir', 'sikaman', 'fck'
    ]
    if custom_words:
        condensed_keywords.extend([normalize_text(cw) for cw in custom_words if cw])

    for kw in condensed_keywords:
        if kw and kw in condensed:
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


async def unmute_after(bot: Bot, chat_id: int, user_id: int, delay: int = 15):
    """Foydalanuvchini 15 soniyadan so'ng avtomatik muterdan chiqarish."""
    await asyncio.sleep(delay)
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions
        )
    except Exception:
        pass


# -------------------------------------------------------------
# 3. Censor Middleware (Guruhdagi har bir xabarni tekshiradi)
# -------------------------------------------------------------
class CensorMiddleware(BaseMiddleware):
    """
    Guruhdagi barcha xabarlarni routerlardan OLDIN tekshiruvchi middleware.
    So'kinish aniqlansa:
    - Xabar darhol o'chiriladi.
    - Admin bo'lsa: qat'iy ogohlantiriladi.
    - Oddiy a'zo bo'lsa: 15 soniyaga mute qilinadi.
    - Xabar boshqa handlerlarga o'tkazilmaydi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.chat:
            return await handler(event, data)

        if event.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await handler(event, data)

        if not event.from_user or event.from_user.is_bot:
            return await handler(event, data)

        chat_id = event.chat.id
        user = event.from_user

        # Filtr o'chirilgan bo'lsa tekshirmaymiz
        if not is_censor_enabled(chat_id):
            return await handler(event, data)

        text = event.text or event.caption or ""
        if not text:
            return await handler(event, data)

        custom_words = get_custom_bad_words(chat_id)
        if not is_profane(text, custom_words):
            return await handler(event, data)

        # Haqorat aniqlandi!
        bot: Bot = data.get("bot") or event.bot

        # 1. Haqoratli xabarni zudlik bilan o'chirish
        try:
            await bot.delete_message(chat_id=chat_id, message_id=event.message_id)
        except Exception:
            pass

        # 2. Xatti-harakat: Admin bo'lsa ogohlantirish, oddiy a'zo bo'lsa 15 soniya mute
        is_admin = await is_telegram_admin(chat_id, user.id, bot)
        if is_admin:
            try:
                warn_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ <b>{escape(user.full_name)}</b>, admin bo'lib turib so'kinmang! "
                         f"Iltimos, boshqalarga o'rnak bo'ling va guruhda madaniyatni saqlang!",
                    parse_mode="HTML"
                )
                asyncio.create_task(delete_message_later(bot, chat_id, warn_msg.message_id, delay=15))
            except Exception:
                pass
        else:
            # Telegram Bot API: until_date < 30s bo'lsa cheksiz (forever) deb hisoblaydi.
            # Shuning uchun Telegramga 35s xavfsizlik muddati beramiz va bot 15s dan so'ng avtomatik yechadi!
            until_date = datetime.now(timezone.utc) + timedelta(seconds=35)
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
                # 15 soniyadan so'ng avtomatik yozishni tiklash
                asyncio.create_task(unmute_after(bot, chat_id, user.id, delay=15))

                warn_msg = await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ <b>{escape(user.full_name)}</b>, guruhda so'kinish va haqorat qat'iyan taqiqlangan!\n"
                         f"<i>Siz 15 soniyaga yozishdan cheklandingiz (Mute).</i>",
                    parse_mode="HTML"
                )
                asyncio.create_task(delete_message_later(bot, chat_id, warn_msg.message_id, delay=15))
            except TelegramBadRequest:
                pass
            except Exception:
                pass

        # Xabar haqoratli bo'lgani sababli keyingi handlerlarga o'tkazmaymiz
        return


# -------------------------------------------------------------
# 4. Admin Buyruqlari (/censor on/off, /addbadword, /delbadword, /badwords)
# -------------------------------------------------------------

@router.message(Command("censor"))
async def cmd_censor(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        if message.chat.type == ChatType.PRIVATE:
            await message.reply(
                "ℹ️ <b>So'kinish filtri (Censor) guruhlar uchun mo'ljallangan!</b>\n\n"
                "1. Botni guruhingizga qo'shing va <b>Admin</b> huquqini bering.\n"
                "2. Guruh ichida <code>/censor on</code> yoki <code>/censor off</code> deb yozing.\n\n"
                "<i>Standart holatda barcha guruhlarda filtr yoqilgan (ON) holatda bo'ladi.</i>",
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
                f"💡 <i>Eslatma: Bu so'z allaqachon botning standart bazasida ham mavjud va barcha guruhlarda avtomatik bloklanadi.</i>",
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
