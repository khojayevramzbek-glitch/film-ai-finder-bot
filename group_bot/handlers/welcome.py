from html import escape
from aiogram import Router, types, F, Bot

router = Router()


@router.message(F.new_chat_members)
async def on_user_joined(message: types.Message, bot: Bot):
    """Yangi a'zo guruhga qo'shilganda chiroyli kutib olish (Welcome)."""
    chat_title = message.chat.title or "Близкий 🫂"

    try:
        from group_bot.database import is_bot_enabled, get_chat_full_settings
    except ImportError:
        from database import is_bot_enabled, get_chat_full_settings

    for user in message.new_chat_members:
        if user.id == bot.id:
            # Botning o'zi guruhga qo'shilganda
            await message.answer(
                f"👋 Assalomu alaykum! <b>{escape(chat_title)}</b> guruhiga qo'shilganimdan xursandman.\n\n"
                "Statistika va moderatorlik to'liq ishlashi uchun menga <b>Administrator</b> huquqlarini bering.",
                parse_mode="HTML"
            )
        elif not user.is_bot and is_bot_enabled(message.chat.id):
            settings = get_chat_full_settings(message.chat.id)
            if not settings.get("welcome_enabled", 1):
                continue

            template = settings.get("welcome_text", "Assalomu alaykum, {name}! Guruhimizga xush kelibsiz!")
            welcome_text = template.replace("{name}", f"<b>{escape(user.full_name)}</b>")
            await message.answer(welcome_text, parse_mode="HTML")
