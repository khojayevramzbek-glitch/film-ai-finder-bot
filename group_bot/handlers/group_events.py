import re
from html import escape
from aiogram import Router, types, F, Bot
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from .admin_commands import is_admin

router = Router()

# Havola (link) va telegram username/kanallarni aniqlash uchun regex
LINK_PATTERN = re.compile(
    r"(https?://\S+|t\.me/\S+|telegram\.me/\S+|@[a-zA-Z0-9_]{4,})",
    re.IGNORECASE
)


@router.message(F.new_chat_members)
async def on_user_joined(message: types.Message, bot: Bot):
    """Yangi a'zo guruhga qo'shilganda kutib olish."""
    for user in message.new_chat_members:
        if user.id == bot.id:
            # Botning o'zi guruhga qo'shilganda
            await message.answer(
                "👋 Assalomu alaykum! Meni guruhingizga qo'shganingiz uchun rahmat.\n\n"
                "To'liq ishlashim va guruh xavfsizligini ta'minlashim uchun menga <b>Administrator</b> huquqlarini bering.\n"
                "Buyruqlar ro'yxatini ko'rish: <code>/help</code>",
                parse_mode="HTML"
            )
        else:
            # Yangi foydalanuvchi qo'shilganda
            welcome_text = (
                f"🎉 Xush kelibsiz, <b>{escape(user.full_name)}</b>!\n\n"
                f"<b>{escape(message.chat.title or 'Guruhimiz')}</b>ga xush kelibsiz.\n"
                "Iltimos, guruh qoidalari bilan tanishib chiqing: <code>/rules</code>"
            )
            await message.answer(welcome_text, parse_mode="HTML")


@router.message(F.left_chat_member)
async def on_user_left(message: types.Message, bot: Bot):
    """Foydalanuvchi guruhni tark etganda (ixtiyoriy bildirishnoma)."""
    user = message.left_chat_member
    if user.id != bot.id:
        await message.answer(
            f"👋 <b>{escape(user.full_name)}</b> guruhni tark etdi.",
            parse_mode="HTML"
        )


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def filter_links_and_spam(message: types.Message, bot: Bot):
    """Guruhda oddiy foydalanuvchilar tomonidan yuborilgan reklama va linklarni o'chirish."""
    # Agar xabar buyruq bo'lsa yoki matn bo'lmasa tekshirmaymiz
    text = message.text or message.caption
    if not text or text.startswith("/"):
        return

    # Foydalanuvchi admin bo'lsa ruxsat beriladi
    if await is_admin(message.chat.id, message.from_user.id, bot):
        return

    # Agar xabarda havola (link) aniqlansa
    if LINK_PATTERN.search(text):
        try:
            await message.delete()
            warning_msg = await message.answer(
                f"⚠️ <b>{escape(message.from_user.full_name)}</b>, guruhda reklama va havolalar (link) tarqatish taqiqlanadi!",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            # Agar botda xabarlarni o'chirish huquqi bo'lmasa
            pass
