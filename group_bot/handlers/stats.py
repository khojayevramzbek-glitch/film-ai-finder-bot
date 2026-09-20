import re
from html import escape
from aiogram import Router, types
from aiogram.enums import ChatType
from group_bot.database import get_24h_stats

router = Router()

# Faqat ruxsat berilgan username(lar)
ALLOWED_USERNAMES = {"wdablyu", "khojayev_ramz"}

# Lotin va Kirill alifbosidagi 'stata', 'стата', 'stat', 'стат', '/stata' va h.k.
# s/с, t/т, a/а
STATA_REGEX = re.compile(
    r"^\s*(/?[sс][tт][aа][tт][aа]?|[sс][tт][aа][tт][sс]?)\b",
    re.IGNORECASE
)


def is_authorized_user(user: types.User | None) -> bool:
    """Faqat ruxsat berilgan foydalanuvchilarni tekshirish."""
    if not user or not user.username:
        return False
    return user.username.lower() in ALLOWED_USERNAMES


@router.message(lambda msg: bool(STATA_REGEX.search((msg.text or msg.caption or "").strip())))
async def check_stata_command(message: types.Message):
    # Faqat ruxsat berilganlar uchun (@wdablyu, @khojayev_ramz). Boshqalarga hech qanday javob bermaymiz!
    if not is_authorized_user(message.from_user):
        return

    # Guruh yoki chat ID sini aniqlash
    chat_id = message.chat.id
    chat_title = message.chat.title or "Guruh"

    # So'nggi 24 soatlik statistika
    rows, total_msgs, total_users = get_24h_stats(chat_id, limit=50)

    if not rows or total_msgs == 0:
        await message.reply(
            f"📊 <b>{escape(chat_title)}</b> guruhida so'nggi 24 soat ichida hali hech qanday xabar yozilmadi.",
            parse_mode="HTML",
            disable_notification=True
        )
        return

    # Ro'yxatni shakllantirish
    lines = [
        f"📊 <b>{escape(chat_title)} — So'nggi 24 soatlik faollik (Top aktivlar):</b>\n"
    ]

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for idx, row in enumerate(rows, start=1):
        medal = medals.get(idx, f"<b>{idx}.</b>")
        user_name = escape(row["full_name"])
        # '@' dan keyin ko'rinmas belgi (\u200b) qo'yiladi.
        # Bu foydalanuvchiga Telegram orqali 'tag' (mention notification) bormasligini ta'minlaydi
        username_part = f" (@\u200b{escape(row['username'])})" if row.get("username") else ""
        msg_count = row["msg_count"]

        lines.append(f"{medal} {user_name}{username_part} — <b>{msg_count}</b> ta xabar")

    lines.append("\n" + "—" * 25)
    lines.append(f"👥 <b>Faol a'zolar:</b> {total_users} kishi")
    lines.append(f"💬 <b>Jami yozilgan xabarlar:</b> {total_msgs} ta")

    response_text = "\n".join(lines)
    # disable_notification=True butunlay tovushsiz (silent) yuborilishini ta'minlaydi
    await message.reply(response_text, parse_mode="HTML", disable_notification=True)
