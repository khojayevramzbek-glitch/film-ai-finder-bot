import re
from datetime import datetime, timedelta, timezone
from html import escape
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest

router = Router()

# Guruhdagi ogohlantirishlar (chat_id, user_id) -> count
_warnings: dict[tuple[int, int], int] = {}


async def is_admin(chat_id: int, user_id: int, bot: Bot) -> bool:
    """Foydalanuvchi guruh admini yoki egasi ekanligini tekshiradi."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


def parse_time(time_str: str) -> timedelta | None:
    """Vaqt satrini (masalan, 10m, 2h, 1d) timedelta ga aylantiradi."""
    match = re.match(r"^(\d+)([smhd])$", time_str.strip().lower())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return timedelta(seconds=val)
    elif unit == "m":
        return timedelta(minutes=val)
    elif unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    return None


@router.message(Command("ban"))
async def cmd_ban(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    # Buyruq bergan odam adminmi?
    if not await is_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    # Xabarga javob (reply) qilinganmi?
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("❗ Foydalanuvchini ban qilish uchun uning xabariga reply qilib <code>/ban</code> deb yozing.", parse_mode="HTML")
        return

    target_user = message.reply_to_message.from_user

    # Bot yoki adminni ban qilishdan saqlash
    if target_user.id == bot.id:
        await message.reply("😅 O'zimni guruhdan chiqara olmayman!")
        return

    if await is_admin(message.chat.id, target_user.id, bot):
        await message.reply("❌ Adminlarni guruhdan chiqarib bo'lmaydi!")
        return

    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user.id)
        await message.answer(
            f"🚫 Foydalanuvchi <b>{escape(target_user.full_name)}</b> guruhdan chiqarildi va bloklandi.",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        await message.reply(f"⚠️ Xatolik yuz berdi: Botda yetarli admin huquqi yo'q bo'lishi mumkin.\n({e.message})")


@router.message(Command("unban"))
async def cmd_unban(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    if not await is_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("❗ Foydalanuvchini blokdan chiqarish uchun uning xabariga reply qiling.", parse_mode="HTML")
        return

    target_user = message.reply_to_message.from_user

    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=target_user.id, only_if_banned=True)
        await message.answer(
            f"✅ Foydalanuvchi <b>{escape(target_user.full_name)}</b> blokdan chiqarildi.",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        await message.reply(f"⚠️ Xatolik: {e.message}")


@router.message(Command("mute"))
async def cmd_mute(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    if not await is_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply(
            "❗ Foydalanuvchini yozishdan cheklash uchun uning xabariga reply qilib yozing:\n"
            "Masalan: <code>/mute 15m</code> yoki <code>/mute 2h</code>",
            parse_mode="HTML"
        )
        return

    target_user = message.reply_to_message.from_user

    if target_user.id == bot.id or await is_admin(message.chat.id, target_user.id, bot):
        await message.reply("❌ Admin yoki botni cheklab bo'lmaydi!")
        return

    # Vaqtni aniqlash (standart: 15 daqiqa)
    args = message.text.split(maxsplit=1)
    duration = timedelta(minutes=15)
    duration_text = "15 daqiqa"

    if len(args) > 1:
        parsed = parse_time(args[1])
        if parsed:
            duration = parsed
            duration_text = args[1]
        else:
            await message.reply("⚠️ Noto'g'ri vaqt formati! Masalan: <code>/mute 10m</code>, <code>/mute 1h</code>, <code>/mute 1d</code>", parse_mode="HTML")
            return

    until_date = datetime.now(timezone.utc) + duration

    try:
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False
        )
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=permissions,
            until_date=until_date
        )
        await message.answer(
            f"🔇 Foydalanuvchi <b>{escape(target_user.full_name)}</b> {duration_text} ga yozish huquqidan cheklandi.",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        await message.reply(f"⚠️ Xatolik: {e.message}")


@router.message(Command("unmute"))
async def cmd_unmute(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    if not await is_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("❗ Foydalanuvchidan cheklovni olish uchun uning xabariga reply qiling.")
        return

    target_user = message.reply_to_message.from_user

    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=permissions
        )
        await message.answer(
            f"🔊 Foydalanuvchi <b>{escape(target_user.full_name)}</b> uchun yozish cheklovi olib tashlandi.",
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        await message.reply(f"⚠️ Xatolik: {e.message}")


@router.message(Command("warn"))
async def cmd_warn(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    if not await is_admin(message.chat.id, message.from_user.id, bot):
        await message.reply("❌ Bu buyruq faqat guruh adminlari uchun!")
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("❗ Ogohlantirish berish uchun foydalanuvchi xabariga reply qiling.")
        return

    target_user = message.reply_to_message.from_user

    if target_user.id == bot.id or await is_admin(message.chat.id, target_user.id, bot):
        await message.reply("❌ Admin yoki botga ogohlantirish berib bo'lmaydi!")
        return

    key = (message.chat.id, target_user.id)
    count = _warnings.get(key, 0) + 1
    _warnings[key] = count

    if count >= 3:
        _warnings[key] = 0
        # 3 ta ogohlantirish - 1 soatga mute
        until_date = datetime.now(timezone.utc) + timedelta(hours=1)
        try:
            permissions = ChatPermissions(can_send_messages=False)
            await bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target_user.id,
                permissions=permissions,
                until_date=until_date
            )
            await message.answer(
                f"⚠️ Foydalanuvchi <b>{escape(target_user.full_name)}</b> 3 ta ogohlantirish oldi va 1 soatga yozishdan cheklandi.",
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            await message.reply(f"⚠️ Xatolik: {e.message}")
    else:
        await message.answer(
            f"⚠️ Foydalanuvchi <b>{escape(target_user.full_name)}</b> ga ogohlantirish berildi! ({count}/3)\n"
            f"<i>3 ta ogohlantirishdan so'ng foydalanuvchi cheklanadi.</i>",
            parse_mode="HTML"
        )
