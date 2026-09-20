import re
from html import escape
from aiogram import Router, types, Bot, F
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

try:
    from group_bot.database import (
        get_24h_stats,
        is_stats_enabled,
        set_stats_status,
        get_all_group_ids,
    )
except ImportError:
    from database import (
        get_24h_stats,
        is_stats_enabled,
        set_stats_status,
        get_all_group_ids,
    )

router = Router()

ALLOWED_BOT_OWNERS = {"wdablyu", "khojayev_ramz"}
ALLOWED_BOT_OWNER_IDS = {8594505572, 7690283463}

# Lotin va Kirill: 'stata', 'Stata', 'STATA', 'стата', 'Стата', 'СТАТА', '/stata', 'stat'
STATA_REGEX = re.compile(
    r"^\s*(/?[sс][tт][aа][tт][aа]?|[sс][tт][aа][tт][sс]?)\b",
    re.IGNORECASE
)


def is_bot_owner(user: types.User | None) -> bool:
    """Foydalanuvchi bot egasimi (@khojayev_ramz yoki @wdablyu)."""
    if not user:
        return False
    if user.id in ALLOWED_BOT_OWNER_IDS:
        return True
    if user.username and user.username.lower() in ALLOWED_BOT_OWNERS:
        return True
    return False


async def is_group_creator(chat_id: int, user_id: int, bot: Bot) -> bool:
    """Foydalanuvchi guruh egasimi (Creator / Guruhga qo'shgan odam)."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status == ChatMemberStatus.CREATOR
    except Exception:
        return False


def format_top30_stats(chat_title: str, chat_id: int) -> str:
    """Guruh uchun so'nggi 24 soatlik Top 30 statistikani shakllantirish."""
    rows, total_msgs, total_users = get_24h_stats(chat_id, limit=30)

    if not rows or total_msgs == 0:
        return f"📊 <b>{escape(chat_title)}</b> guruhida so'nggi 24 soat ichida hali hech qanday xabar yozilmadi."

    lines = [
        f"📊 <b>{escape(chat_title)} — So'nggi 24 soatlik faollik (Top 30 aktivlar):</b>\n"
    ]

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for idx, row in enumerate(rows, start=1):
        medal = medals.get(idx, f"<b>{idx}.</b>")
        user_name = escape(row["full_name"])
        username_part = f" (@\u200b{escape(row['username'])})" if row.get("username") else ""
        msg_count = row["msg_count"]
        lines.append(f"{medal} {user_name}{username_part} — <b>{msg_count}</b> ta xabar")

    lines.append("\n" + "—" * 25)
    lines.append(f"👥 <b>Faol a'zolar:</b> {total_users} kishi")
    lines.append(f"💬 <b>Jami yozilgan xabarlar:</b> {total_msgs} ta")
    lines.append("<i>🔄 Statistika so'nggi 24 soat bo'yicha real vaqtda yangilanadi.</i>")

    return "\n".join(lines)


@router.message(lambda msg: bool(STATA_REGEX.match((msg.text or msg.caption or "").strip())))
async def check_stata_command(message: types.Message, bot: Bot):
    text = (message.text or message.caption or "").strip()
    tokens = text.split()
    args = tokens[1:] if len(tokens) > 1 else []
    subcmd = args[0].lower() if args else ""
    user = message.from_user

    # =========================================================================
    # 1. SHAXSIY CHATDA (Botimizning ichida - PM)
    # =========================================================================
    if message.chat.type == ChatType.PRIVATE:
        if not user:
            return

        is_owner = is_bot_owner(user)
        all_group_ids = get_all_group_ids()

        # Foydalanuvchiga tegishli (egasi bo'lgan yoki bot egasi ko'ra oladigan) guruhlar
        user_groups = []
        for gid in all_group_ids:
            try:
                chat = await bot.get_chat(gid)
                if is_owner or await is_group_creator(gid, user.id, bot):
                    user_groups.append(chat)
            except Exception:
                continue

        if not user_groups:
            await message.reply(
                "ℹ️ <b>Statistika (Stata) Tizimi:</b>\n\n"
                "Siz hali bot qo'shilgan biror guruhning egasi emassiz.\n"
                "Botni guruhingizga qo'shing va <b>Admin</b> huquqini bering, shunda guruh statistikasini shu yerda ko'rishingiz mumkin bo'ladi!",
                parse_mode="HTML"
            )
            return

        # Agar bitta guruh bo'lsa -> to'g'ridan-to'g'ri uning Top 30 statistikasini chiqaramiz
        if len(user_groups) == 1:
            g = user_groups[0]
            if not is_stats_enabled(g.id):
                await message.reply(
                    f"⚠️ <b>{escape(g.title)}</b> guruhida statistika o'chirilgan.\nYoqish uchun guruhda <code>/stata on</code> deb yozing.",
                    parse_mode="HTML"
                )
                return

            response_text = format_top30_stats(g.title, g.id)
            await message.reply(response_text, parse_mode="HTML", disable_notification=True)
            return

        # Agar bir nechta guruh bo'lsa -> tugmalar orqali tanlash imkonini beramiz
        buttons = []
        for g in user_groups:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📊 {g.title}",
                    callback_data=f"show_stata_{g.id}"
                )
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply(
            "📊 <b>Qaysi guruh statistikasini (Top 30) ko'rmoqchisiz?</b>\nQuyidagilardan birini tanlang:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return

    if message.chat.type == ChatType.CHANNEL:
        return

    # =========================================================================
    # 2. GURUHDA (GROUP / SUPERGROUP)
    # Faqat guruh egasi (Creator) va Bot egasi (@khojayev_ramz) da ishlaydi!
    # Boshqa hech kimda ishlamaydi (bot jim turadi).
    # =========================================================================
    chat_id = message.chat.id
    user_id = user.id if user else 0

    is_owner = is_bot_owner(user)
    is_creator = await is_group_creator(chat_id, user_id, bot)

    # Ruxsat berilmagan bo'lsa -> mutlaqo jim turadi
    if not (is_owner or is_creator):
        return

    # 2.1. SOZLAMALAR: /stata on yoki /stata off
    if subcmd in ["on", "off"]:
        if subcmd == "on":
            set_stats_status(chat_id, True)
            await message.reply("✅ <b>Guruh statistikasi (Stata) YOQILDI!</b>", parse_mode="HTML")
            return
        elif subcmd == "off":
            set_stats_status(chat_id, False)
            await message.reply("⚠️ <b>Guruh statistikasi (Stata) O'CHIRILDI.</b>", parse_mode="HTML")
            return

    # 2.2. STATISTIKANI CHIQARISH (stata / Stata / /stata)
    if not is_stats_enabled(chat_id):
        await message.reply(
            "ℹ️ Ushbu guruhda statistika o'chirilgan. Yoqish uchun: <code>/stata on</code>",
            parse_mode="HTML"
        )
        return

    chat_title = message.chat.title or "Guruh"
    response_text = format_top30_stats(chat_title, chat_id)
    await message.reply(response_text, parse_mode="HTML", disable_notification=True)


@router.callback_query(F.data.startswith("show_stata_"))
async def callback_show_stata(call: CallbackQuery, bot: Bot):
    """Lichkada guruh tanlanganda statistikasini ko'rsatish."""
    try:
        chat_id = int(call.data.replace("show_stata_", ""))
        chat = await bot.get_chat(chat_id)
        if not is_stats_enabled(chat_id):
            await call.message.edit_text(
                f"⚠️ <b>{escape(chat.title)}</b> guruhida statistika o'chirilgan.\nYoqish uchun guruhda <code>/stata on</code> deb yozing.",
                parse_mode="HTML"
            )
            await call.answer()
            return

        response_text = format_top30_stats(chat.title, chat_id)
        await call.message.edit_text(response_text, parse_mode="HTML")
    except Exception as e:
        await call.answer("Guruh statistikasi yuklanmadi.", show_alert=True)
    await call.answer()
