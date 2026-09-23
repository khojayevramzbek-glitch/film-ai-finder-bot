from html import escape
import logging
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

logger = logging.getLogger(__name__)
router = Router()

WEBAPP_URL = "https://uchunrisk-film-ai-finder-bot.hf.space/gradio_api/webapp"

# Guruhda tozalik va intizomni saqlash uchun har bir guruhdagi so'nggi welcome xabari ID si
_last_welcome_messages: dict[int, int] = {}


@router.message(F.new_chat_members)
async def on_user_joined(message: types.Message, bot: Bot):
    """
    Yangi a'zo(lar) guruhga qo'shilganda nufuzli, jiddiy va juda chiroyli kutib olish (Welcome).
    """
    chat_title = message.chat.title or "Guruh"

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

    # 1. Botning o'zi guruhga qo'shilganda
    for user in message.new_chat_members:
        if user.id == bot.id:
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
                            web_app=WebAppInfo(url=f"{WEBAPP_URL}?chat_id={message.chat.id}")
                        )
                    ]]
                )
            )
            return

    # 2. Yangi haqiqiy foydalanuvchilar qo'shilganda
    real_users = [u for u in message.new_chat_members if not u.is_bot]
    if not real_users:
        return

    # Guruhda bot yoqilganmi tekshirish
    if not is_bot_enabled(message.chat.id):
        return

    settings = get_chat_full_settings(message.chat.id)
    if not settings.get("welcome_enabled", 1):
        return

    template = settings.get("welcome_text") or DEFAULT_WELCOME_TEXT

    # O'zgaruvchilarni tayyorlash
    if len(real_users) == 1:
        u = real_users[0]
        mentions_str = f'<a href="tg://user?id={u.id}">{escape(u.full_name)}</a>'
        names_str = escape(u.full_name)
        first_names_str = escape(u.first_name)
        usernames_str = f"@{u.username}" if u.username else escape(u.first_name)
        ids_str = str(u.id)
    else:
        # Bir vaqtda bir nechta odam kirganda chiroyli birlashtirish
        mentions_list = [f'<a href="tg://user?id={u.id}">{escape(u.full_name)}</a>' for u in real_users]
        if len(mentions_list) == 2:
            mentions_str = f"{mentions_list[0]} va {mentions_list[1]}"
        else:
            mentions_str = ", ".join(mentions_list[:-1]) + f" va {mentions_list[-1]}"

        names_str = ", ".join(escape(u.full_name) for u in real_users)
        first_names_str = ", ".join(escape(u.first_name) for u in real_users)
        usernames_str = ", ".join((f"@{u.username}" if u.username else escape(u.first_name)) for u in real_users)
        ids_str = ", ".join(str(u.id) for u in real_users)

    title_str = escape(chat_title)

    # Guruh a'zolari soni
    try:
        count = await bot.get_chat_member_count(message.chat.id)
        count_str = f"{count:,}".replace(",", " ")
    except Exception:
        count_str = ""

    # Guruh qoidalari
    rules_text = get_rules(message.chat.id) or ""
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

    # Tugmalar (Interactive Buttons)
    inline_keyboard = []
    action_row = [
        InlineKeyboardButton(text="📜 Guruh Qoidalari", callback_data=f"welcome_rules:{message.chat.id}")
    ]

    # Agar guruhning ommaviy username'i bo'lsa
    if message.chat.username:
        action_row.append(InlineKeyboardButton(text="🔗 Guruh Silkasi", url=f"https://t.me/{message.chat.username}"))

    inline_keyboard.append(action_row)
    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

    # Guruhda tozalik va intizom: oldingi welcome xabari bo'lsa, o'chirib yangisini qo'yish
    old_welcome_id = _last_welcome_messages.get(message.chat.id)
    if old_welcome_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=old_welcome_id)
        except Exception:
            pass

    try:
        sent_msg = await message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True
        )
        _last_welcome_messages[message.chat.id] = sent_msg.message_id
    except Exception as e:
        logger.error(f"Welcome xabarini yuborishda xatolik: {e}")
        # Agar maxsus formatda xato bo'lsa, xavfsiz zaxira varianti
        try:
            fallback = f"✨ <b>Xush kelibsiz, {mentions_str}!</b>\n\n<b>«{title_str}»</b> guruhimizga marhamat!"
            sent_msg = await message.answer(
                fallback,
                parse_mode="HTML",
                reply_markup=markup,
                disable_web_page_preview=True
            )
            _last_welcome_messages[message.chat.id] = sent_msg.message_id
        except Exception:
            pass


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
