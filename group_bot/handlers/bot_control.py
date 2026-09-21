import re
from html import escape
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

try:
    from group_bot.database import is_bot_enabled, set_bot_status, get_all_group_ids
    from group_bot.handlers.censor import get_user_manageable_groups, is_bot_owner, is_group_creator
except ImportError:
    from database import is_bot_enabled, set_bot_status, get_all_group_ids
    from handlers.censor import get_user_manageable_groups, is_bot_owner, is_group_creator

router = Router()

BOT_STATUS_TEXT = (
    "🔘 <b>Blizkiy Bot Boshqaruvi (Yoqish / O'chirish):</b>\n\n"
    "Ushbu bo'lim orqali botni guruhda to'liq yoqishingiz yoki vaqtincha to'xtatishingiz (pauza) mumkin.\n\n"
    "🛡 <b>Bot O'chirilganda:</b>\n"
    "• Guruhda hech qanday xabarlarni o'chirmaydi va a'zolarni cheklamaydi (mute/ban qilmaydi).\n"
    "• So'kinish va Anti-flood filtrlari vaqtincha to'xtatiladi.\n"
    "• <b>Lekin barcha statistika, sozlamalar, qoidalar va ogohlantirishlar to'liq saqlanib qoladi!</b>\n\n"
    "Quyidagi tugma orqali kerakli guruhda botni bir bosishda yoqing yoki o'chiring:"
)


async def build_bot_status_keyboard(user: types.User, bot: Bot) -> InlineKeyboardMarkup:
    """Foydalanuvchi guruhlari uchun botni yoqish/o'chirish tugmalarini generatsiya qilish."""
    groups = await get_user_manageable_groups(user, bot)
    buttons = []
    for g in groups:
        enabled = is_bot_enabled(g.id)
        status_icon = "🟢 Yoqilgan" if enabled else "🔴 O'chirilgan"
        action_text = "O'chirish ⏸" if enabled else "Yoqish ▶️"
        buttons.append([
            InlineKeyboardButton(
                text=f"{g.title} [{status_icon}] — {action_text}",
                callback_data=f"toggle_bot_{g.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="◀️ Asosiy Menyuga Qaytish", callback_data="menu_back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("toggle_bot_"))
async def callback_toggle_bot(call: CallbackQuery, bot: Bot):
    """Lichkada guruhning bot holatini bitta bosishda yoqish/o'chirish."""
    try:
        chat_id = int(call.data.replace("toggle_bot_", ""))
        user = call.from_user
        if not (is_bot_owner(user) or await is_group_creator(chat_id, user.id, bot)):
            await call.answer("❌ Bu amalni faqat guruh egasi yoki bot admini bajara oladi!", show_alert=True)
            return

        current = is_bot_enabled(chat_id)
        new_status = not current
        set_bot_status(chat_id, new_status)

        kb = await build_bot_status_keyboard(user, bot)
        await call.message.edit_reply_markup(reply_markup=kb)

        alert_text = "🟢 Blizkiy bot guruhda to'liq YOQILDI!" if new_status else "🔴 Blizkiy bot guruhda O'CHIRILDI (pauzaga qo'yildi)!"
        await call.answer(alert_text, show_alert=False)
    except Exception as e:
        await call.answer("Xatolik yuz berdi.", show_alert=True)


BOT_CMD_REGEX = re.compile(r"^\s*(/?(?:bot|blizkiy|blizki))\b", re.IGNORECASE)


@router.message(lambda msg: bool(BOT_CMD_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_bot_control(message: types.Message, bot: Bot):
    """Guruhda yoki lichkada botni yoqish/o'chirish buyruqlari (/bot on, /bot off, /bot)."""
    text = (message.text or message.caption or "").strip()
    tokens = text.split()
    args = tokens[1:] if len(tokens) > 1 else []
    subcmd = args[0].lower() if args else ""
    user = message.from_user

    # 1. SHAXSIY CHATDA (Lichkada)
    if message.chat.type == ChatType.PRIVATE:
        if not user:
            return
        groups = await get_user_manageable_groups(user, bot)
        if not groups:
            await message.reply(
                "ℹ️ <b>Blizkiy Bot Boshqaruvi:</b>\n\n"
                "Siz hali bot qo'shilgan biror guruhning egasi emassiz.\n"
                "Botni guruhingizga qo'shib <b>Admin</b> qiling, shunda botni shu yerda ham yoqib/o'chira olasiz!",
                parse_mode="HTML"
            )
            return

        if subcmd in ["on", "yoq"]:
            for g in groups:
                set_bot_status(g.id, True)
            await message.reply("✅ Barcha guruhlaringizda Blizkiy bot <b>YOQILDI 🟢</b>!", parse_mode="HTML")
            return
        elif subcmd in ["off", "ochir", "o'chir"]:
            for g in groups:
                set_bot_status(g.id, False)
            await message.reply("⏸ Barcha guruhlaringizda Blizkiy bot <b>O'CHIRILDI 🔴</b> (pauzaga qo'yildi).", parse_mode="HTML")
            return

        kb = await build_bot_status_keyboard(user, bot)
        await message.reply(
            BOT_STATUS_TEXT,
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    if message.chat.type == ChatType.CHANNEL:
        return

    # 2. GURUHDA
    chat_id = message.chat.id
    if not (is_bot_owner(user) or await is_group_creator(chat_id, user.id, bot)):
        await message.reply("❌ Bu buyruq faqat guruh egasi yoki bot bosh admini uchun!")
        return

    if not subcmd:
        current = is_bot_enabled(chat_id)
        status_text = "🟢 Yoqilgan (Faol)" if current else "🔴 O'chirilgan (Pauzada)"
        await message.reply(
            f"ℹ️ <b>Blizkiy Bot Holati:</b> {status_text}\n\n"
            f"O'zgartirish uchun:\n"
            f"• <code>/bot on</code> yoki <code>bot on</code> — Botni guruhda yoqish\n"
            f"• <code>/bot off</code> yoki <code>bot off</code> — Botni guruhda o'chirish (pauza)\n\n"
            f"<i>Bot o'chirilganda ham barcha statistika va sozlamalar to'liq saqlanib qoladi!</i>",
            parse_mode="HTML"
        )
        return

    if subcmd in ["on", "yoq"]:
        set_bot_status(chat_id, True)
        await message.reply(
            "✅ <b>Blizkiy bot guruhda to'liq YOQILDI 🟢!</b>\n"
            "<i>Barcha himoya tizimlari, filtrlari va buyruqlar faollashdi.</i>",
            parse_mode="HTML"
        )
    elif subcmd in ["off", "ochir", "o'chir"]:
        set_bot_status(chat_id, False)
        await message.reply(
            "⏸ <b>Blizkiy bot guruhda to'liq O'CHIRILDI 🔴 (pauzaga qo'yildi).</b>\n"
            "<i>Bot vaqtincha xabarlarni o'chirmaydi va a'zolarni cheklamaydi. Barcha statistika va sozlamalar to'liq saqlanib qoladi!</i>\n\n"
            "Qayta yoqish uchun: <code>/bot on</code>",
            parse_mode="HTML"
        )
    else:
        await message.reply("❗ Noto'g'ri buyruq. <code>/bot on</code> yoki <code>/bot off</code> deb yozing.", parse_mode="HTML")
