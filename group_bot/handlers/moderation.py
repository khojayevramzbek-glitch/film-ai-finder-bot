import re
from datetime import datetime, timedelta, timezone
from html import escape
from aiogram import Router, types, Bot
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest

from group_bot.database import (
    add_warn, get_warns, remove_warn, reset_warns, 
    get_user_24h_stat, get_user_by_username, get_user_by_id
)

router = Router()

ALLOWED_USERNAMES = {"wdablyu", "khojayev_ramz"}


class TargetUser:
    def __init__(self, user_id: int, full_name: str, username: str | None = None):
        self.id = user_id
        self.full_name = full_name
        self.username = username


async def is_admin_or_allowed(chat_id: int, user: types.User | TargetUser, bot: Bot) -> bool:
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
MUTE_REGEX = re.compile(r"^/?(?:[sс]?[mм][uу][tт][eе]?|[mм][uу][tт][eе]?)\b", re.IGNORECASE)
UNMUTE_REGEX = re.compile(r"^/?(?:[uу][nн][mм][uу][tт][eе]?|[aа][nн][mм][uу][tт][eе]?)\b", re.IGNORECASE)
WARN_REGEX = re.compile(r"^/?([wв][aа][rр][nн])\b", re.IGNORECASE)
UNWARN_REGEX = re.compile(r"^/?([uу][nн][wв][aа][rр][nн]|[aа][nн][wв][aа][rр][nн])\b", re.IGNORECASE)
BAN_REGEX = re.compile(r"^/?([bб][aа][nн])\b", re.IGNORECASE)
UNBAN_REGEX = re.compile(r"^/?([uу][nн][bб][aа][nн]|[rр][aа][zз][bб][aа][nн])\b", re.IGNORECASE)
USER_STAT_REGEX = re.compile(r"^/?([sс][tт][aа][tт][aа][sс][iі]|[mм][yу][sс][tт][aа][tт])\b", re.IGNORECASE)


def is_moderation_command(message: types.Message) -> bool:
    text = (message.text or message.caption or "").strip()
    if not text:
        return False
    cmd = text.split()[0] if text.split() else ""
    return bool(
        MUTE_REGEX.match(cmd) or UNMUTE_REGEX.match(cmd) or
        WARN_REGEX.match(cmd) or UNWARN_REGEX.match(cmd) or
        BAN_REGEX.match(cmd) or UNBAN_REGEX.match(cmd) or
        USER_STAT_REGEX.match(cmd)
    )


async def resolve_target_and_args(message: types.Message, bot: Bot) -> tuple[TargetUser | None, list[str], str | None]:
    """
    Xabardan maqsadli foydalanuvchi (TargetUser) va qolgan argumentlarni ajratib oladi:
    1. Reply qilingan bo'lsa -> reply qilingan foydalanuvchi.
    2. Message text_mention entities bo'lsa -> entity.user.
    3. Args ichida @username bo'lsa -> bazadan qidirish.
    4. Args ichida raqamli ID bo'lsa -> ID bo'yicha olish.
    Qaytaradi: (target_user, remaining_args, error_message)
    """
    text = (message.text or message.caption or "").strip()
    tokens = text.split()
    cmd = tokens[0] if tokens else ""
    args = tokens[1:]

    # 1. Reply qilinganmi?
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return TargetUser(u.id, u.full_name, u.username), args, None

    # 2. Text mention entity (Telegram orqali ism bilan tag qilingan)
    entities = message.entities or message.caption_entities or []
    for ent in entities:
        if ent.type == "text_mention" and ent.user:
            u = ent.user
            name_text = text[ent.offset:ent.offset + ent.length]
            remaining_args = [a for a in args if a not in name_text]
            return TargetUser(u.id, u.full_name, u.username), remaining_args, None

    # 3. @username yoki User ID ni args ichidan qidirish
    target_user = None
    remaining_args = []
    lookup_error = None

    for arg in args:
        if not target_user and arg.startswith("@"):
            raw_username = arg.lstrip("@")
            user_data = get_user_by_username(message.chat.id, raw_username)
            if user_data:
                target_user = TargetUser(
                    user_id=user_data["user_id"],
                    full_name=user_data["full_name"],
                    username=user_data.get("username")
                )
            else:
                lookup_error = f"⚠️ <b>@{escape(raw_username)}</b> bazadan topilmadi!\nFoydalanuvchi hali guruhda xabar yozmagan bo'lishi mumkin. Xabariga reply qilib ko'ring."
        elif not target_user and arg.isdigit() and len(arg) >= 6:
            uid = int(arg)
            user_data = get_user_by_id(uid)
            full_name = user_data["full_name"] if user_data else f"Foydalanuvchi [{uid}]"
            username = user_data.get("username") if user_data else None
            target_user = TargetUser(user_id=uid, full_name=full_name, username=username)
        else:
            remaining_args.append(arg)

    if lookup_error and not target_user:
        return None, remaining_args, lookup_error

    if not target_user:
        return None, remaining_args, "❗ Foydalanuvchini ko‘rsating: uning xabariga reply qiling yoki <code>@username</code> deb yozing."

    return target_user, remaining_args, None


@router.message(is_moderation_command)
async def handle_moderation_commands(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    text = (message.text or message.caption or "").strip()
    if not text:
        return

    tokens = text.split()
    cmd = tokens[0] if tokens else ""

    # Faqat admin yoki ruxsat berilganlar uchun tekshirish
    is_authorized = await is_admin_or_allowed(message.chat.id, message.from_user, bot)
    if not is_authorized:
        return

    # 1. MUTE: /mute, mute, мут
    if MUTE_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        if target_user.id == bot.id or await is_admin_or_allowed(message.chat.id, target_user, bot):
            await message.reply("❌ Admin yoki botni cheklab bo'lmaydi!")
            return

        # Vaqtni aniqlash (qolgan argumentlar orasidan yoki standart 15m)
        duration = timedelta(minutes=15)
        duration_text = "15m"

        for arg in rem_args:
            parsed = parse_time(arg)
            if parsed:
                duration = parsed
                duration_text = arg
                break

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
            u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
            await message.answer(
                f"🔇 Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} {duration_text} ga yozishdan cheklandi.",
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            await message.reply(f"⚠️ Xatolik: Botda tegishli admin huquqlari yo'q ({e.message})")
        return

    # 2. UNMUTE: /unmute, unmute, анмут
    if UNMUTE_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

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
            u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
            await message.answer(
                f"🔊 Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} uchun yozish cheklovi olib tashlandi.",
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            await message.reply(f"⚠️ Xatolik: {e.message}")
        return

    # 3. WARN: /warn, warn, варн
    if WARN_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        if target_user.id == bot.id or await is_admin_or_allowed(message.chat.id, target_user, bot):
            await message.reply("❌ Admin yoki botga ogohlantirish berib bo'lmaydi!")
            return

        new_count = add_warn(message.chat.id, target_user.id)
        u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""

        if new_count >= 3:
            reset_warns(message.chat.id, target_user.id)
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
                    f"⚠️ Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} 3 ta ogohlantirish oldi va <b>24 soatga</b> yozishdan cheklandi!",
                    parse_mode="HTML"
                )
            except TelegramBadRequest as e:
                await message.reply(f"⚠️ Xatolik: {e.message}")
        else:
            await message.answer(
                f"⚠️ Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} ga ogohlantirish berildi! ({new_count}/3)\n"
                "<i>3 ta ogohlantirishdan so'ng 24 soatga cheklanadi.</i>",
                parse_mode="HTML"
            )
        return

    # 4. UNWARN: /unwarn, unwarn, анварн
    if UNWARN_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        rem_count = remove_warn(message.chat.id, target_user.id)
        u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
        await message.answer(
            f"✅ <b>{escape(target_user.full_name)}</b>{u_tag} dan 1 ta ogohlantirish olib tashlandi. (Qoldi: {rem_count}/3)",
            parse_mode="HTML"
        )
        return

    # 5. BAN: /ban, ban, бан
    if BAN_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        if target_user.id == bot.id or await is_admin_or_allowed(message.chat.id, target_user, bot):
            await message.reply("❌ Admin yoki botni guruhdan chiqarib bo'lmaydi!")
            return

        try:
            await bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user.id)
            u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
            await message.answer(
                f"🚫 Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} guruhdan chiqarildi va bloklandi.",
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            await message.reply(f"⚠️ Xatolik: {e.message}")
        return

    # 6. UNBAN: /unban, unban, разбан
    if UNBAN_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        try:
            await bot.unban_chat_member(chat_id=message.chat.id, user_id=target_user.id, only_if_banned=True)
            u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
            await message.answer(
                f"✅ Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} blokdan chiqarildi.",
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            await message.reply(f"⚠️ Xatolik: {e.message}")
        return

    # 7. Shaxsiy statistika: statasi / mystat
    if USER_STAT_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if target_user:
            count = get_user_24h_stat(message.chat.id, target_user.id)
            u_name = escape(target_user.full_name)
            username_part = f" (@\u200b{escape(target_user.username)})" if target_user.username else ""
            await message.reply(
                f"📊 <b>{u_name}</b>{username_part} so'nggi 24 soat ichida <b>{count}</b> ta xabar yozgan.",
                parse_mode="HTML",
                disable_notification=True
            )
        return
