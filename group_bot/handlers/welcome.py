from html import escape
from aiogram import Router, types, F, Bot

router = Router()


@router.message(F.new_chat_members)
async def on_user_joined(message: types.Message, bot: Bot):
    """Yangi a'zo guruhga qo'shilganda chiroyli kutib olish (Welcome)."""
    chat_title = message.chat.title or "Близкий 🫂"

    for user in message.new_chat_members:
        if user.id == bot.id:
            # Botning o'zi guruhga qo'shilganda
            await message.answer(
                f"👋 Assalomu alaykum! <b>{escape(chat_title)}</b> guruhiga qo'shilganimdan xursandman.\n\n"
                "Statistika va moderatorlik to'liq ishlashi uchun menga <b>Administrator</b> huquqlarini bering.",
                parse_mode="HTML"
            )
        elif not user.is_bot:
            # Yangi foydalanuvchi qo'shilganda (kreativ va samimiy)
            welcome_text = (
                f"🫂 <b>{escape(chat_title)}</b> — yaqinlar davrasiga xush kelibsiz!\n\n"
                f"Xush ko‘rdik, <b>{escape(user.full_name)}</b> 👋\n"
                "Bu yerda zerikish yo‘q — davramizga qo‘shiling va doimo <b>aktiv bo‘ling!</b> ⚡️"
            )
            await message.answer(welcome_text, parse_mode="HTML")
