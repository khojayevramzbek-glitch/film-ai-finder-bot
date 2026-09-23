import re
import asyncio
from datetime import datetime, timedelta, timezone
from html import escape
from aiogram import Router, types, Bot
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import ChatPermissions
from aiogram.exceptions import TelegramBadRequest

from group_bot.database import (
    add_warn, get_warns, remove_warn, reset_warns, 
    get_user_24h_stat, get_user_by_username, get_user_by_id,
    get_chat_full_settings, format_duration,
    set_admin_virtual_mute, remove_admin_virtual_mute, is_admin_virtually_muted
)

router = Router()

ALLOWED_USERNAMES = {"wdablyu", "khojayev_ramz"}
ALLOWED_USER_IDS = {8594505572, 7690283463}


class TargetUser:
    def __init__(self, user_id: int, full_name: str, username: str | None = None):
        self.id = user_id
        self.full_name = full_name
        self.username = username


async def is_admin_or_allowed(chat_id: int, user: types.User | TargetUser, bot: Bot) -> bool:
    """Foydalanuvchi guruh adminimi yoki bot egasimi (@wdablyu, @khojayev_ramz)."""
    if getattr(user, "id", None) in ALLOWED_USER_IDS:
        return True
    if user.username and user.username.lower() in ALLOWED_USERNAMES:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user.id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


async def is_group_admin(chat_id: int, user_id: int, bot: Bot) -> bool:
    """Foydalanuvchi guruh adminimi yoki egasimi."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


async def is_group_creator(chat_id: int, user_id: int, bot: Bot) -> bool:
    """Foydalanuvchi guruh asosiy egasimi (Creator)."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status == ChatMemberStatus.CREATOR
    except Exception:
        return False


TIME_REGEX = re.compile(
    r"^(\d+)\s*(s|sec|sek|sekund|soniya|с|сек|секунд|"
    r"m|min|daq|daqiqa|м|мин|минут|минута|"
    r"h|hr|soat|hour|hours|ч|час|часа|часов|"
    r"d|kun|day|days|д|день|дня|дней|"
    r"w|wk|hafta|week|weeks|нед|неделя|недели|недель|"
    r"mo|moth|month|months|oy|мес|месяц|месяца|месяцев|"
    r"y|yr|year|years|yil|г|год|года|лет)$",
    re.IGNORECASE
)


def parse_time(time_str: str) -> tuple[timedelta, int, str] | None:
    """
    Vaqt satrini (masalan: 10s, 5m, 2h, 1d, 1w, 1mo, 1y) timedelta,
    jami soniyalar va chiroyli o'zbekcha matnga aylantiradi.
    """
    if not time_str:
        return None
    match = TIME_REGEX.match(time_str.strip().lower())
    if not match:
        return None

    val = int(match.group(1))
    unit = match.group(2).lower()

    if unit in ("s", "sec", "sek", "sekund", "soniya", "с", "сек", "секунд"):
        seconds = val
    elif unit in ("m", "min", "daq", "daqiqa", "м", "мин", "минут", "минуta"):
        seconds = val * 60
    elif unit in ("h", "hr", "soat", "hour", "hours", "ч", "час", "часа", "часов"):
        seconds = val * 3600
    elif unit in ("d", "kun", "day", "days", "д", "день", "дня", "дней"):
        seconds = val * 86400
    elif unit in ("w", "wk", "hafta", "week", "weeks", "нед", "неделя", "недели", "недель"):
        seconds = val * 604800
    elif unit in ("mo", "moth", "month", "months", "oy", "мес", "месяц", "месяца", "месяцев"):
        seconds = val * 2592000
    elif unit in ("y", "yr", "year", "years", "yil", "г", "год", "года", "лет"):
        seconds = val * 31536000
    else:
        return None

    duration = timedelta(seconds=seconds)
    duration_text = format_duration(seconds)
    return (duration, seconds, duration_text)


async def unmute_after(bot: Bot, chat_id: int, user_id: int, delay: int):
    """Qisqa muddatli (30 soniyadan kam) mute uchun taymer."""
    await asyncio.sleep(delay)
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)
    except Exception:
        pass


# Buyruqlar regexlari (Lotin va Kirill alifbosida)
# Moderatsiya buyruqlari qat'iy ravishda '/' belgisi bilan boshlanishi SHART!
# Bu oddiy suhbatdagi 'ban', 'mute', 'ban qilaman' kabi so'zlarni tasodifan buyruq deb tushunmaslik uchun zarur.
MUTE_REGEX = re.compile(r"^/(?:[sс]?[mм][uу][tт][eе]?|[mм][uу][tт][eе]?)\b", re.IGNORECASE)
UNMUTE_REGEX = re.compile(r"^/(?:[uу][nн][mм][uу][tт][eе]?|[aа][nн][mм][uу][tт][eе]?)\b", re.IGNORECASE)
WARN_REGEX = re.compile(r"^/([wв][aа][rр][nн])\b", re.IGNORECASE)
UNWARN_REGEX = re.compile(r"^/([uу][nн][wв][aа][rр][nн]|[aа][nн][wв][aа][rр][nн])\b", re.IGNORECASE)
BAN_REGEX = re.compile(r"^/([bб][aа][nн])\b", re.IGNORECASE)
UNBAN_REGEX = re.compile(r"^/([uу][nн][bб][aа][nн]|[rр][aа][zз][bб][aа][nн])\b", re.IGNORECASE)
USER_STAT_REGEX = re.compile(r"^/([sс][tт][aа][tт][aа][sс][iі]|[mм][yу][sс][tт][aа][tт])\b", re.IGNORECASE)


def is_moderation_command(message: types.Message) -> bool:
    text = (message.text or message.caption or "").strip()
    if not text or not text.startswith("/"):
        return False
    tokens = text.split()
    cmd = tokens[0].split("@")[0] if tokens else ""
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
    if not text or not text.startswith("/"):
        return

    tokens = text.split()
    cmd = tokens[0].split("@")[0] if tokens else ""

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

        # 1. Botning o'zini cheklab bo'lmaydi
        if target_user.id == bot.id:
            await message.reply("❌ Botni cheklab bo'lmaydi!")
            return

        # 2. Bot egalari mutlaqo daxlsiz (@khojayev_ramz, @wdablyu)
        if target_user.id in ALLOWED_USER_IDS or (target_user.username and target_user.username.lower() in ALLOWED_USERNAMES):
            await message.reply("❌ Bot egasini cheklab bo'lmaydi!")
            return

        # 3. Guruh asosiy egasi (Creator) daxlsiz
        if await is_group_creator(message.chat.id, target_user.id, bot):
            await message.reply("❌ Guruh asosiy egasini (Creator) cheklab bo'lmaydi!")
            return

        # Vaqtni aniqlash (qolgan argumentlar orasidan yoki guruh sozlamasidagi vaqt)
        settings = get_chat_full_settings(message.chat.id)
        default_mute_sec = int(settings.get("flood_mute_seconds", 900))
        duration = timedelta(seconds=default_mute_sec)
        total_seconds = default_mute_sec
        duration_text = format_duration(default_mute_sec)

        found_time = False
        # 1. Bitta argument bo'yicha qidirish (masalan: 10s, 5m, 2h, 1d, 1w, 1mo, 1y)
        for arg in rem_args:
            parsed = parse_time(arg)
            if parsed:
                duration, total_seconds, duration_text = parsed
                found_time = True
                break

        # 2. Ketma-ket 2 ta argument bo'yicha qidirish (masalan: "10" "s", "1" "hafta", "2" "oy", "1" "yil")
        if not found_time and len(rem_args) >= 2:
            for i in range(len(rem_args) - 1):
                parsed = parse_time(rem_args[i] + rem_args[i + 1])
                if parsed:
                    duration, total_seconds, duration_text = parsed
                    found_time = True
                    break

        target_is_admin = await is_group_admin(message.chat.id, target_user.id, bot)
        u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""

        # Agar nishondagi foydalanuvchi ADMIN bo'lsa -> Virtual Mute (0.1s tezkor o'chirish)
        if target_is_admin:
            set_admin_virtual_mute(message.chat.id, target_user.id, total_seconds)
            await message.answer(
                f"🔇 <b>Admin {escape(target_user.full_name)}</b>{u_tag} <b>{duration_text}ga</b> Mute qilindi (Virtual Mute)!\n"
                f"<i>(Jazo davomida admin yozgan barcha xabarlar 0.1s ichida avtomatik o'chirib tashlanadi)</i>",
                parse_mode="HTML"
            )
            return

        # Agar oddiy a'zo bo'lsa -> Telegram API orqali restrictChatMember
        until_date = datetime.now(timezone.utc) + timedelta(seconds=max(total_seconds, 35))

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
            if total_seconds < 35:
                asyncio.create_task(unmute_after(bot, message.chat.id, target_user.id, delay=total_seconds))

            await message.answer(
                f"🔇 Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} <b>{duration_text}ga</b> yozishdan cheklandi (Mute).",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            # Agar Telegram API ruxsat bermasa -> Virtual Mute fallback
            set_admin_virtual_mute(message.chat.id, target_user.id, total_seconds)
            await message.answer(
                f"🔇 <b>{escape(target_user.full_name)}</b>{u_tag} <b>{duration_text}ga</b> Mute qilindi (Virtual Mute).",
                parse_mode="HTML"
            )
        return

    # 2. UNMUTE: /unmute, unmute, анмут
    if UNMUTE_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        # Virtual Mutedan tozalash (agar bor bo'lsa)
        was_virtually_muted = is_admin_virtually_muted(message.chat.id, target_user.id)
        if was_virtually_muted:
            remove_admin_virtual_mute(message.chat.id, target_user.id)

        # Telegram API orqali ham cheklovni olib tashlash
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
        except TelegramBadRequest:
            pass

        u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
        await message.answer(
            f"🔊 <b>{escape(target_user.full_name)}</b>{u_tag} uchun yozish cheklovi olib tashlandi (Unmute).",
            parse_mode="HTML"
        )
        return

    # 3. WARN: /warn, warn, варн
    if WARN_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        if target_user.id == bot.id:
            await message.reply("❌ Botga ogohlantirish berib bo'lmaydi!")
            return

        if target_user.username and target_user.username.lower() in ALLOWED_USERNAMES:
            await message.reply("❌ Bot egasiga ogohlantirish berib bo'lmaydi!")
            return

        try:
            target_member = await bot.get_chat_member(message.chat.id, target_user.id)
        except Exception:
            target_member = None

        if target_member and target_member.status == ChatMemberStatus.CREATOR:
            await message.reply("❌ Guruh egasi (Creator)ga ogohlantirish berib bo'lmaydi!")
            return

        is_target_admin = bool(target_member and target_member.status == ChatMemberStatus.ADMINISTRATOR)

        settings = get_chat_full_settings(message.chat.id)
        warn_limit = int(settings.get("warn_limit", 10))
        warn_action = settings.get("warn_action", "smart")
        warn_mute_sec = int(settings.get("warn_mute_seconds", 3600))
        if warn_action == "mute_7d":
            warn_mute_sec = 604800
        elif warn_action == "mute":
            warn_mute_sec = 3600

        new_count = add_warn(message.chat.id, target_user.id)
        u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
        role_label = "Admin" if is_target_admin else "Foydalanuvchi"

        if new_count >= warn_limit:
            reset_warns(message.chat.id, target_user.id)
            if is_target_admin:
                # 10 ta warn olgan admin adminlikdan olinsin
                try:
                    await bot.promote_chat_member(
                        chat_id=message.chat.id,
                        user_id=target_user.id,
                        is_anonymous=False,
                        can_manage_chat=False,
                        can_post_messages=False,
                        can_edit_messages=False,
                        can_delete_messages=False,
                        can_post_stories=False,
                        can_edit_stories=False,
                        can_delete_stories=False,
                        can_manage_video_chats=False,
                        can_restrict_members=False,
                        can_promote_members=False,
                        can_change_info=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_manage_topics=False
                    )
                    await message.answer(
                        f"🚨 Admin <b>{escape(target_user.full_name)}</b>{u_tag} {warn_limit} ta ogohlantirish oldi va <b>adminlik lavozimidan olindi</b>!",
                        parse_mode="HTML"
                    )
                except TelegramBadRequest as e:
                    await message.answer(
                        f"🚨 Admin <b>{escape(target_user.full_name)}</b>{u_tag} {warn_limit} ta ogohlantirish oldi!\n"
                        f"⚠️ Bot uni lavozimdan ololmadi ({e.message}). Guruh egasi ushbu adminni o'zi lavozimidan olishi zarur.",
                        parse_mode="HTML"
                    )
            else:
                # 10 ta warn olgan oddiy foydalanuvchi 1 soat mute olsin
                if warn_action == "ban":
                    try:
                        await bot.ban_chat_member(chat_id=message.chat.id, user_id=target_user.id)
                        await message.answer(
                            f"🚫 Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} {warn_limit} ta ogohlantirish oldi va guruhdan chiqarildi (Ban)!",
                            parse_mode="HTML"
                        )
                    except TelegramBadRequest as e:
                        await message.reply(f"⚠️ Xatolik: {e.message}")
                else:
                    until_date = datetime.now(timezone.utc) + timedelta(seconds=warn_mute_sec)
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
                        dur_str = format_duration(warn_mute_sec)
                        await message.answer(
                            f"⚠️ Foydalanuvchi <b>{escape(target_user.full_name)}</b>{u_tag} {warn_limit} ta ogohlantirish oldi va <b>{dur_str}ga</b> yozishdan cheklandi (Mute)!",
                            parse_mode="HTML"
                        )
                    except TelegramBadRequest as e:
                        await message.reply(f"⚠️ Xatolik: {e.message}")
        else:
            action_desc = "adminlik lavozimidan olinadi." if is_target_admin else f"{format_duration(warn_mute_sec)}ga mute qilinadi."
            await message.answer(
                f"⚠️ {role_label} <b>{escape(target_user.full_name)}</b>{u_tag} ga ogohlantirish berildi! ({new_count}/{warn_limit})\n"
                f"<i>{warn_limit} ta ogohlantirish to'planganda {action_desc}</i>",
                parse_mode="HTML"
            )
        return

    # 4. UNWARN: /unwarn, unwarn, анварн
    if UNWARN_REGEX.match(cmd):
        target_user, rem_args, err = await resolve_target_and_args(message, bot)
        if err:
            await message.reply(err, parse_mode="HTML")
            return

        settings = get_chat_full_settings(message.chat.id)
        warn_limit = int(settings.get("warn_limit", 10))

        rem_count = remove_warn(message.chat.id, target_user.id)
        u_tag = f" (@{escape(target_user.username)})" if target_user.username else ""
        await message.answer(
            f"✅ <b>{escape(target_user.full_name)}</b>{u_tag} dan 1 ta ogohlantirish olib tashlandi. (Qoldi: {rem_count}/{warn_limit})",
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
