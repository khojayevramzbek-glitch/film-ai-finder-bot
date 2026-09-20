import re
from datetime import datetime, timedelta, timezone
from html import escape
from aiogram import Router, types, Bot
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest

from database import add_warn, get_warns, remove_warn, reset_warns, get_user_24h_stat

router = Router()

ALLOWED_USERNAMES = {"wdablyu", "khojayev_ramz"}


async def is_admin_or_allowed(chat_id: int, user: types.User, bot: Bot) -> bool:
    """Foydalanuvchi guruh adminimi yoki bot egasimi (@wdablyu, @khojayev_ramz)."""
    if user.username and user.username.lower() in ALLOWED_USERNAMES:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


def parse_time(time_str: str) -> timedelta | None:
    """Vaqt satrini (masalan: 10m, 2h, 1d) timedelta ga aylantiradi."""
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


# Buyruqlar regexlari (Lotin va Kirill alifbosida)
MUTE_REGEX = re.compile(r"^/?(?:[sс]?[mм][uу][tт][eе]?|[mм][uу][tт][eе]?)(?:\s+(\w+))?$", re.IGNORECASE)
UNMUTE_REGEX = re.compile(r"^/?(?:[uу][nн][mм][uу][tт][eе]?|[aа][nн][mм][uу][tт][eе]?)$", re.IGNORECASE)
WARN_REGEX = re.compile(r"^/?([wв][aа][rр][nн])$", re.IGNORECASE)
UNWARN_REGEX = re.compile(r"^/?([uу][nн][wв][aа][rр][nн]|[aа][nн][wв][aа][rр][nн])$", re.IGNORECASE)
BAN_REGEX = re.compile(r"^/?([bб][aа][nн])$", re.IGNORECASE)
UNBAN_REGEX = re.compile(r"^/?([uу][nн][bб][aа][nн]|[rр][aа][zз][bб][aа][nн])$", re.IGNORECASE)
USER_STAT_REGEX = re.compile(r"^/?([sс][tт][aа][tт][aа][sс][iі]|[mм][yу][sс][tт][aа][tт])$", re.IGNORECASE)


def is_moderation_command(message: types.Message) -> bool:
    text = (message.text or message.caption or "").strip()
    if not text:
        return False
    return bool(
        MUTE_REGEX.match(text) or UNMUTE_REGEX.match(text) or
        WARN_REGEX.match(text) or UNWARN_REGEX.match(text) or
        BAN_REGEX.match(text) or UNBAN_REGEX.match(text) or
        USER_STAT_REGEX.match(text)
    )


@router.message(is_moderation_command)
async def handle_moderation_commands(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    text = (message.text or message.caption or "").strip()
    if not text:
        return

    # 1. Shaxsiy statistika: statasi / mystat
    if USER_STAT_REGEX.match(text):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            return
        target_user = message.reply_to_message.from_user
        count = get_user_24h_stat(message.chat.id, target_user.id)
        u_name = escape(target_user.full_name)
        username_part = f" (@\u200b{escape(target_user.username)})" if target_user.username else ""
        await message.reply(
            f"📊 <b>{u_name}</b>{username_part} so'nggi 24 soat ichida <b>{count}</b> ta xabar yozgan.",
            parse_mode="HTML",
            disable_notification=True
        )
        return

    # Faqat admin yoki ruxsat berilganlar uchun tekshirish
    is_authorized = await is_admin_or_allowed(message.chat.id, message.from_user, bot)
    if not is_authorized:
        return

    # 2. MUTE: /mute, mute, мут 10m
    mute_match = MUTE_REGEX.match(text)
    if mute_match:
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply("❗ Foydalanuvchini cheklash uchun uning xabariga reply qilib yozing (masalan: <code>mute 15m</code>).", parse_mode="HTML")
            return

        target_user = message.reply_to_message.from_user
        if target_user.id == bot.id or await is_admin_or_allowed(message.chat.id, target_user, bot):
            await message.reply("❌ Admin yoki botni cheklab bo'lmaydi!")
            return

        time_arg = mute_match.group(1) or "15m"
        duration = parse_time(time_arg) or timedelta(minutes=15)
        duration_text = time_arg if parse_time(time_arg) else "15m"
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
                f"🔇 Foydalanuvchi <b>{escape(target_user.full_name)}</b> {duration_text} ga yozishdan cheklandi.",
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            await message.reply(f"⚠️ Xatolik: Botda tegishli admin huquqlari yo'q ({e.message})")
        return

    # 3. UNMUTE: /unmute, unmute, анмут
    if UNMUTE_REGEX.match(text):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply("❗ Cheklovni olish uchun foydalanuvchi xabariga reply qiling.")
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
        return

    # 4. WARN: /warn, warn, варн
    if WARN_REGEX.match(text):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply("❗ Ogohlantirish berish uchun foydalanuvchi xabariga reply qiling.")
            return

        target_user = message.reply_to_message.from_user
        if target_user.id == bot.id or await is_admin_or_allowed(message.chat.id, target_user, bot):
            await message.reply("❌ Admin yoki botga ogohlantirish berib bo'lmaydi!")
            return

        new_count = add_warn(message.chat.id, target_user.id)
        if new_count >= 3:
            reset_warns(message.chat.id, target_user.id)
            # 24 soatga mute
            until_date = datetime.now(timezone.utc) + timedelta(hours=24)
            try:
                permissions = ChatPermissions(can_send_messages=False)
                await bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=target_user.id,
                    permissions=permissions,
                    until_date=until_date
                )
                await message.answer(
                    f"⚠️ Foydalanuvchi <b>{escape(target_user.full_name)}</b> 3 ta ogohlantirish oldi va <b>24 soatga</b> yozishdan cheklandi!",
                    parse_mode="HTML"
                )
            except TelegramBadRequest as e:
                await message.reply(f"⚠️ Xatolik: {e.message}")
        else:
            await message.answer(
                f"⚠️ Foydalanuvchi <b>{escape(target_user.full_name)}</b> ga ogohlantirish berildi! ({new_count}/3)\n"
                "<i>3 ta ogohlantirishdan so'ng 24 soatga cheklanadi.</i>",
                parse_mode="HTML"
            )
        return

    # 5. UNWARN: /unwarn, unwarn, анварн
    if UNWARN_REGEX.match(text):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply("❗ Ogohlantirishni olib tashlash uchun foydalanuvchi xabariga reply qiling.")
            return

        target_user = message.reply_to_message.from_user
        rem_count = remove_warn(message.chat.id, target_user.id)
        await message.answer(
            f"✅ <b>{escape(target_user.full_name)}</b> dan 1 ta ogohlantirish olib tashlandi. (Qoldi: {rem_count}/3)",
            parse_mode="HTML"
        )
        return

    # 6. BAN: /ban, ban, бан
    if BAN_REGEX.match(text):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply("❗ Foydalanuvchini guruhdan chiqarish uchun uning xabariga reply qiling.")
            return

        target_user = message.reply_to_message.from_user
        if target_user.id == bot.id or await is_admin_or_allowed(message.chat.id, target_user, bot):
            await message.reply("❌ Admin yoki botni guruhdan chiqarib bo'lmaydi!")
            return

        try:
            await bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user.id)
            await message.answer(
                f"🚫 Foydalanuvchi <b>{escape(target_user.full_name)}</b> guruhdan chiqarildi va bloklandi.",
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            await message.reply(f"⚠️ Xatolik: {e.message}")
        return

    # 7. UNBAN: /unban, unban, разбан
    if UNBAN_REGEX.match(text):
        if not message.reply_to_message or not message.reply_to_message.from_user:
            await message.reply("❗ Blokdan chiqarish uchun foydalanuvchi xabariga reply qiling.")
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
        return
