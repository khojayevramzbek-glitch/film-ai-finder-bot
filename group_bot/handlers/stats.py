import re
from html import escape
from aiogram import Router, types, Bot
from aiogram.enums import ChatType, ChatMemberStatus

try:
    from group_bot.database import (
        get_24h_stats,
        is_stats_enabled,
        set_stats_status,
        is_stats_public,
        set_stats_public,
    )
except ImportError:
    from database import (
        get_24h_stats,
        is_stats_enabled,
        set_stats_status,
        is_stats_public,
        set_stats_public,
    )

router = Router()

ALLOWED_USERNAMES = {"wdablyu", "khojayev_ramz"}

# Lotin va Kirill: 'stata', 'стата', 'stat', 'стат', '/stata'
STATA_REGEX = re.compile(
    r"^\s*(/?[sс][tт][aа][tт][aа]?|[sс][tт][aа][tт][sс]?)\b",
    re.IGNORECASE
)


async def is_admin(chat_id: int, user_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


@router.message(lambda msg: bool(STATA_REGEX.match((msg.text or msg.caption or "").strip())))
async def check_stata_command(message: types.Message, bot: Bot):
    text = (message.text or message.caption or "").strip()
    tokens = text.split()
    args = tokens[1:] if len(tokens) > 1 else []
    subcmd = args[0].lower() if args else ""

    # 1. SHAXSIY CHATDA (Lichkada)
    if message.chat.type == ChatType.PRIVATE:
        await message.reply(
            "📊 <b>Guruh Statistikasi (Stata):</b>\n\n"
            "Ushbu funksiya guruhdagi 24 soatlik xabarlar va eng faol a'zolarni (Top aktivlarni) hisoblab boradi.\n\n"
            "⚙️ <b>Guruh Buyruqlari:</b>\n"
            "• <code>stata</code> yoki <code>/stata</code> — Guruh faolligi reytingini ko'rish\n"
            "• <code>statasi @username</code> — Foydalanuvchining shaxsiy xabarlar soni\n"
            "• <code>/stata on</code> — Statistikani yoqish (Admin)\n"
            "• <code>/stata off</code> — Statistikani o'chirish (Admin)\n"
            "• <code>/stata public</code> — Barcha a'zolar ko'rishi uchun ruxsat\n"
            "• <code>/stata admin</code> — Faqat adminlar ko'rishi uchun cheklash",
            parse_mode="HTML"
        )
        return

    if message.chat.type == ChatType.CHANNEL:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    is_adm = (message.from_user and message.from_user.username and message.from_user.username.lower() in ALLOWED_USERNAMES) or await is_admin(chat_id, user_id, bot)

    # 2. SOZLAMALAR: /stata on, /stata off, /stata public, /stata admin
    if subcmd in ["on", "off", "public", "admin"]:
        if not is_adm:
            await message.reply("❌ Bu sozlamani faqat guruh adminlari o'zgartirishi mumkin!")
            return

        if subcmd == "on":
            set_stats_status(chat_id, True)
            await message.reply("✅ <b>Guruh statistikasi (Stata) YOQILDI!</b>", parse_mode="HTML")
            return
        elif subcmd == "off":
            set_stats_status(chat_id, False)
            await message.reply("⚠️ <b>Guruh statistikasi (Stata) O'CHIRILDI.</b>", parse_mode="HTML")
            return
        elif subcmd == "public":
            set_stats_public(chat_id, True)
            await message.reply(
                "🌐 <b>Statistika endi BARCHA a'zolar uchun ochiq!</b>\n<i>Istalgan a'zo <code>stata</code> deb yozib reytingni ko'rishi mumkin.</i>",
                parse_mode="HTML"
            )
            return
        elif subcmd == "admin":
            set_stats_public(chat_id, False)
            await message.reply("🔒 <b>Statistika FAQAT ADMINLAR uchun cheklandi!</b>", parse_mode="HTML")
            return

    # 3. STATISTIKANI CHIQARISH (stata / /stata)
    if not is_stats_enabled(chat_id):
        if is_adm:
            await message.reply("ℹ️ Ushbu guruhda statistika o'chirilgan. Yoqish uchun: <code>/stata on</code>", parse_mode="HTML")
        return

    # Ko'rish huquqi: agar public bo'lmasa va admin bo'lmasa -> rad etamiz
    if not is_adm and not is_stats_public(chat_id):
        return

    chat_title = message.chat.title or "Guruh"
    rows, total_msgs, total_users = get_24h_stats(chat_id, limit=50)

    if not rows or total_msgs == 0:
        await message.reply(
            f"📊 <b>{escape(chat_title)}</b> guruhida so'nggi 24 soat ichida hali hech qanday xabar yozilmadi.",
            parse_mode="HTML",
            disable_notification=True
        )
        return

    lines = [
        f"📊 <b>{escape(chat_title)} — So'nggi 24 soatlik faollik (Top aktivlar):</b>\n"
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

    response_text = "\n".join(lines)
    await message.reply(response_text, parse_mode="HTML", disable_notification=True)
