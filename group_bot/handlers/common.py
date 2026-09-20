from aiogram import Router, types
from aiogram.filters import Command
from aiogram.enums import ChatType
from html import escape

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type == ChatType.PRIVATE:
        text = (
            f"Assalomu alaykum, <b>{escape(message.from_user.full_name)}</b>!\n\n"
            "Men Telegram guruhlarini boshqarish, yangi a'zolarni kutib olish va guruhda "
            "tartibni saqlash uchun yaratilgan botman.\n\n"
            "<b>Botni ishlatish uchun:</b>\n"
            "1. Meni guruhingizga qo'shing.\n"
            "2. Menga guruhda <b>Administrator</b> huquqlarini bering.\n"
            "3. Guruhda <code>/help</code> buyrug'ini yuboring."
        )
        await message.answer(text, parse_mode="HTML")
    else:
        await message.reply(
            "Bot guruhda faol ishlamoqda! Buyruqlar ro'yxatini ko'rish uchun <code>/help</code> deb yozing.",
            parse_mode="HTML"
        )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "<b>📋 Bot Buyruqlari:</b>\n\n"
        "<b>Umumiy buyruqlar:</b>\n"
        "• <code>/info</code> — Guruh haqida ma'lumot (ID, a'zolar soni)\n"
        "• <code>/rules</code> — Guruh qoidalari\n"
        "• <code>/help</code> — Ushbu yordam xabari\n\n"
        "<b>👮‍♂️ Admin buyruqlari (xabarga reply qilib yoziladi):</b>\n"
        "• <code>/ban</code> — Foydalanuvchini guruhdan chiqarish\n"
        "• <code>/unban</code> — Foydalanuvchi blokini ochish\n"
        "• <code>/mute &lt;vaqt&gt;</code> — Foydalanuvchini yozishdan cheklash (masalan: <code>/mute 10m</code>, <code>/mute 2h</code>)\n"
        "• <code>/unmute</code> — Yozish cheklovini bekor qilish\n"
        "• <code>/warn</code> — Foydalanuvchiga ogohlantirish berish (3 ta ogohlantirishda cheklanadi)"
    )
    await message.reply(help_text, parse_mode="HTML")

@router.message(Command("rules"))
async def cmd_rules(message: types.Message):
    rules_text = (
        "<b>📜 Guruh Qoidalari:</b>\n\n"
        "1. Bir-biringizni hurmat qiling, haqorat va kamsitishlarga yo'l qo'yilmaydi.\n"
        "2. Reklama, spam va ruxsatsiz havolalar (linklar) yuborish taqiqlanadi.\n"
        "3. Mavzudan tashqari (offtop) xabarlarni ko'p yubormang.\n"
        "4. Adminlar talablariga rioya qiling.\n\n"
        "<i>Qoidalarni buzgan foydalanuvchilar guruhdan chiqariladi yoki cheklanadi.</i>"
    )
    await message.reply(rules_text, parse_mode="HTML")

@router.message(Command("info"))
async def cmd_info(message: types.Message):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            f"Sizning ID raqamingiz: <code>{message.from_user.id}</code>\n"
            f"Ismingiz: {escape(message.from_user.full_name)}",
            parse_mode="HTML"
        )
        return

    chat_id = message.chat.id
    chat_title = message.chat.title or "Noma'lum"
    member_count = await message.bot.get_chat_member_count(chat_id)

    info_text = (
        f"<b>ℹ️ Guruh Ma'lumotlari:</b>\n\n"
        f"<b>Nomi:</b> {escape(chat_title)}\n"
        f"<b>ID:</b> <code>{chat_id}</code>\n"
        f"<b>A'zolar soni:</b> {member_count}\n"
        f"<b>Sizning ID:</b> <code>{message.from_user.id}</code>"
    )
    await message.reply(info_text, parse_mode="HTML")
