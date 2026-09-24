import time
from html import escape
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from group_bot.config import get_webapp_url
from group_bot.database import upsert_known_user

logger = logging.getLogger(__name__)
router = Router()

# Guruhda tozalik va intizomni saqlash uchun har bir guruhdagi so'nggi welcome xabari ID si
_last_welcome_messages: dict[int, int] = {}
# Bir vaqtda bir xil foydalanuvchiga ikkita welcome ketib qolishini oldini olish kesh-xotirasi (10 soniya)
_recent_welcomes: dict[tuple[int, int], float] = {}


def _should_welcome_user(chat_id: int, user_id: int) -> bool:
    """Foydalanuvchiga so'nggi 10 soniyada welcome yuborilgan bo'lsa, qayta yubormaslik."""
    now = time.time()
    last_time = _recent_welcomes.get((chat_id, user_id), 0.0)
    if now - last_time < 10.0:
        return False
    _recent_welcomes[(chat_id, user_id)] = now
    # Kesh hajmini cheklash
    if len(_recent_welcomes) > 500:
        for k in list(_recent_welcomes.keys())[:100]:
            if now - _recent_welcomes[k] > 60.0:
                del _recent_welcomes[k]
    return True


async def send_welcome_card(
    bot: Bot,
    chat_id: int,
    chat_title: str,
    chat_username: str | None,
    users: list[types.User],
    is_test: bool = False,
    reply_to_msg_id: int | None = None
) -> None:
    """
    Nufuzli, jiddiy va chiroyli kutib olish kartasini shakllantirib, guruhga yuborish.
    Oldingi welcome xabarini avtomatik tozalab turadi.
    """
    try:
        from group_bot.database import (
            is_bot_enabled,
            get_chat_full_settings,
            get_rules,
            DEFAULT_WELCOME_TEXT
        )
    except ImportError:
        from database import (
            is_bot_enabled,
            get_chat_full_settings,
            get_rules,
            DEFAULT_WELCOME_TEXT
        )

    # Agar test bo'lmasa, bot yoqilganligini tekshirish
    if not is_test and not is_bot_enabled(chat_id):
        return

    settings = get_chat_full_settings(chat_id)
    if not is_test and not settings.get("welcome_enabled", 1):
        return

    template = settings.get("welcome_text") or DEFAULT_WELCOME_TEXT

    # O'zgaruvchilarni tayyorlash
    if len(users) == 1:
        u = users[0]
        mentions_str = f'<a href="tg://user?id={u.id}">{escape(u.full_name)}</a>'
        names_str = escape(u.full_name)
        first_names_str = escape(u.first_name)
        usernames_str = f"@{u.username}" if u.username else escape(u.first_name)
        ids_str = str(u.id)
    else:
        mentions_list = [f'<a href="tg://user?id={u.id}">{escape(u.full_name)}</a>' for u in users]
        if len(mentions_list) == 2:
            mentions_str = f"{mentions_list[0]} va {mentions_list[1]}"
        else:
            mentions_str = ", ".join(mentions_list[:-1]) + f" va {mentions_list[-1]}"

        names_str = ", ".join(escape(u.full_name) for u in users)
        first_names_str = ", ".join(escape(u.first_name) for u in users)
        usernames_str = ", ".join((f"@{u.username}" if u.username else escape(u.first_name)) for u in users)
        ids_str = ", ".join(str(u.id) for u in users)

    title_str = escape(chat_title)

    # A'zolar soni
    try:
        count = await bot.get_chat_member_count(chat_id)
        count_str = f"{count:,}".replace(",", " ")
    except Exception:
        count_str = ""

    # Guruh qoidalari
    rules_text = get_rules(chat_id) or ""
    rules_str = escape(rules_text) if rules_text else "O‘zaro hurmat va madaniyat saqlanishi shart."

    # Shablonni almashtirish
    welcome_text = template
    welcome_text = welcome_text.replace("{mention}", mentions_str)
    welcome_text = welcome_text.replace("{name}", names_str)
    welcome_text = welcome_text.replace("{first_name}", first_names_str)
    welcome_text = welcome_text.replace("{username}", usernames_str)
    welcome_text = welcome_text.replace("{id}", ids_str)
    welcome_text = welcome_text.replace("{user_id}", ids_str)
    welcome_text = welcome_text.replace("{title}", title_str)
    welcome_text = welcome_text.replace("{chat_title}", title_str)
    welcome_text = welcome_text.replace("{count}", count_str)
    welcome_text = welcome_text.replace("{members_count}", count_str)
    welcome_text = welcome_text.replace("{rules}", rules_str)

    if is_test:
        welcome_text = "🧪 <b>[Sinov Rejimi / Test Welcome]</b>\n\n" + welcome_text

    # Tugmalar (Interactive Buttons)
    inline_keyboard = []
    action_row = [
        InlineKeyboardButton(text="📜 Guruh Qoidalari", callback_data=f"welcome_rules:{chat_id}")
    ]

    # Guruh silkasini aniqlash (bazadan, username yoki bot taklif havolasidan)
    group_link = None
    try:
        from group_bot.database import get_chat_invite_link, set_chat_invite_link
        group_link = get_chat_invite_link(chat_id)
    except Exception:
        pass

    if not group_link:
        if chat_username:
            group_link = f"https://t.me/{chat_username.lstrip('@')}"
        else:
            try:
                group_link = await bot.export_chat_invite_link(chat_id)
                set_chat_invite_link(chat_id, group_link)
            except Exception:
                pass

    if group_link and str(group_link).strip().startswith("http"):
        action_row.append(InlineKeyboardButton(text="🔗 Guruh Silkasi", url=str(group_link).strip()))

    inline_keyboard.append(action_row)
    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    # Oldingi welcome xabarini o'chirish (tozalikni saqlash)
    if not is_test:
        old_welcome_id = _last_welcome_messages.get(chat_id)
        if old_welcome_id:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=old_welcome_id)
            except Exception:
                pass

    try:
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True,
            reply_to_message_id=reply_to_msg_id
        )
        if not is_test:
            _last_welcome_messages[chat_id] = sent_msg.message_id
    except Exception as e:
        logger.error(f"Welcome xabarini yuborishda xatolik: {e}")
        # Xavfsiz fallback varianti
        try:
            fallback = f"✨ <b>Xush kelibsiz, {mentions_str}!</b>\n\n<b>«{title_str}»</b> guruhimizga marhamat!"
            sent_msg = await bot.send_message(
                chat_id=chat_id,
                text=fallback,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True,
                reply_to_message_id=reply_to_msg_id
            )
            if not is_test:
                _last_welcome_messages[chat_id] = sent_msg.message_id
        except Exception:
            pass


@router.message(F.new_chat_members)
async def on_user_joined_message(message: types.Message, bot: Bot):
    """
    Yangi a'zo(lar) guruhga qo'shilganda (Message orqali).
    """
    chat_title = message.chat.title or "Guruh"

    # 1. Botning o'zi guruhga qo'shilganda
    for user in message.new_chat_members:
        if user.id == bot.id:
            bot_info = await bot.get_me()
            bot_username = bot_info.username or "oken_sherda_bot"
            await message.answer(
                f"👑 <b>Assalomu alaykum!</b>\n\n"
                f"<b>«{escape(chat_title)}»</b> jamoasiga qo‘shilganimdan mamnunman. "
                f"Men guruhda tartib-intizom, so‘kinish va spamlardan tozalash hamda statistikani yurituvchi aqlli moderatorman.\n\n"
                f"<blockquote>🛡 <b>To‘liq ishlashim uchun:</b>\n"
                f"Menga guruhda <b>Administrator</b> huquqlarini berishingizni so‘rayman.</blockquote>\n\n"
                f"<i>Barcha sozlamalarni Telegram Mini App orqali boshqarishingiz mumkin.</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="⚙️ Guruhni Sozlash (Mini App)",
                            url=f"https://t.me/{bot_username}?start=chat_{message.chat.id}"
                        )
                    ]]
                )
            )
            return

    # 2. Yangi haqiqiy foydalanuvchilar
    for u in message.new_chat_members:
        if not u.is_bot:
            upsert_known_user(u.id, u.full_name, u.username, message.chat.id)

    real_users = [u for u in message.new_chat_members if not u.is_bot and _should_welcome_user(message.chat.id, u.id)]
    if not real_users:
        return

    await send_welcome_card(
        bot=bot,
        chat_id=message.chat.id,
        chat_title=chat_title,
        chat_username=message.chat.username,
        users=real_users
    )


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_user_joined_chat_member(event: types.ChatMemberUpdated, bot: Bot):
    """
    Yangi a'zo guruhga havola orqali qo'shilganda yoki guruhda 'Xush kelibsiz' xizmat xabarlari
    yashirilgan (hide join messages) bo'lsa ham welcome kafolatli ishlashi uchun.
    """
    if event.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    user = event.new_chat_member.user
    if user.is_bot:
        return

    upsert_known_user(user.id, user.full_name, user.username, event.chat.id)

    if not _should_welcome_user(event.chat.id, user.id):
        return

    chat_title = event.chat.title or "Guruh"
    await send_welcome_card(
        bot=bot,
        chat_id=event.chat.id,
        chat_title=chat_title,
        chat_username=event.chat.username,
        users=[user]
    )


@router.message(Command("testwelcome", "welcometest"))
async def cmd_test_welcome(message: types.Message, bot: Bot):
    """
    Adminlar yoki bot egasi guruhda welcome qanday ko'rinishini zudlik bilan sinab ko'rishi uchun.
    """
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.reply("ℹ️ Ushbu buyruq faqat guruhlarda ishlaydi!")
        return

    caller = message.from_user
    if not caller:
        return

    chat_title = message.chat.title or "Guruh"
    await send_welcome_card(
        bot=bot,
        chat_id=message.chat.id,
        chat_title=chat_title,
        chat_username=message.chat.username,
        users=[caller],
        is_test=True,
        reply_to_msg_id=message.message_id
    )


@router.message(Command("setlink", "qoshlink", "link"))
async def cmd_set_link(message: types.Message, bot: Bot):
    """Guruh taklif havolasini (silkasi) sozlash buyrug'i."""
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.reply("ℹ️ Ushbu buyruq faqat guruhlarda ishlaydi!")
        return

    from group_bot.database import is_user_authorized_for_chat, set_chat_invite_link
    user_id = message.from_user.id if message.from_user else 0

    is_admin = False
    try:
        cm = await message.chat.get_member(user_id)
        if cm.status in ("creator", "administrator"):
            is_admin = True
    except Exception:
        pass

    if not is_admin and not is_user_authorized_for_chat(message.chat.id, user_id):
        await message.reply("⛔️ Bu buyruq faqat guruh adminlari yoki bot egasi uchun!")
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            "ℹ️ <b>Guruh silkasini kiritish uchun havola bilan birga yozing:</b>\n\n"
            "Misol: <code>/setlink https://t.me/+PM3yYk0OwA04MDJi</code>",
            parse_mode="HTML"
        )
        return

    new_link = parts[1].strip()
    if not (new_link.startswith("https://t.me/") or new_link.startswith("http://t.me/")):
        await message.reply("⚠️ Havola noto‘g‘ri formatda! <code>https://t.me/...</code> ko‘rinishida bo‘lishi shart.", parse_mode="HTML")
        return

    set_chat_invite_link(message.chat.id, new_link)
    await message.reply(
        f"✅ <b>Guruh silkasi muvaffaqiyatli saqlandi!</b>\n\n"
        f"🔗 <b>Havola:</b> {new_link}\n\n"
        f"<i>Endi yangi a'zolar kirganda yoki /testwelcome qilinganda «🔗 Guruh Silkasi» tugmasi ushbu havolaga yo‘naltiradi.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True
    )


@router.callback_query(F.data.startswith("welcome_rules:"))
async def on_welcome_rules_clicked(call: types.CallbackQuery, bot: Bot):
    """
    Salomlashish xabaridagi '📜 Guruh Qoidalari' tugmasi bosilganda qoidalarni ko'rsatish.
    """
    try:
        chat_id = int(call.data.split(":")[1])
    except Exception:
        chat_id = call.message.chat.id if call.message else 0

    try:
        from group_bot.database import get_rules, get_chat_title
    except ImportError:
        from database import get_rules, get_chat_title

    rules = get_rules(chat_id)
    title = (get_chat_title(chat_id) or "Guruh").strip()

    if not rules or not rules.strip():
        await call.answer(
            "ℹ️ Ushbu guruh uchun maxsus qoidalar kiritilmagan.\n\n"
            "Asosiy talab: O‘zaro hurmat, so‘kinmaslik va reklama tarqatmaslik!",
            show_alert=True
        )
        return

    rules_clean = rules.strip()

    # Telegram modal alert (popup) 200 ta belgigacha sig'adi
    if len(rules_clean) <= 190:
        await call.answer(f"📜 «{title}» qoidalari:\n\n{rules_clean}", show_alert=True)
    else:
        # Uzun qoidalar bo'lsa, alertda qisqa bildirib, chatga chiroyli blockquote bilan yuboramiz
        await call.answer("📜 Guruh qoidalari:", show_alert=False)
        await call.message.reply(
            f"📜 <b>«{escape(title)}» Guruh Qoidalari:</b>\n\n"
            f"<blockquote>{escape(rules_clean)}</blockquote>\n"
            f"<i>Barcha a'zolardan ushbu qoidalarga qat'iy rioya qilish so'raladi.</i>",
            parse_mode="HTML"
        )
