import asyncio
import re
import time
from datetime import datetime, timezone, timedelta
from html import escape
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.enums import ChatType

try:
    from group_bot.database import (
        set_user_sleep,
        get_user_sleep,
        remove_user_sleep,
    )
except ImportError:
    from database import (
        set_user_sleep,
        get_user_sleep,
        remove_user_sleep,
    )

router = Router()

# Toshkent vaqt mintaqasi (UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))

# Maxsus ruxsat berilgan 2 ta foydalanuvchi
ALLOWED_SLEEP_USER_IDS = {8594505572, 7690283463}
ALLOWED_SLEEP_USERNAMES = {"khojayev_ramz", "wdablyu"}

TRACKED_SLEEP_USERS = {
    8594505572: {
        "canonical_username": "khojayev_ramz",
        "display_name": "Ramzbek",
        "regex": re.compile(r'(?i)\b(@?khojayev_ramz|ramz|razm|ramzbek|рамз|разм|рамзбек)\b')
    },
    7690283463: {
        "canonical_username": "wdablyu",
        "display_name": "Wdablyu",
        "regex": re.compile(r'(?i)\b(@?wdablyu|dublyu|dablyu|дублю|вдаблю|даблю|дабл)\b')
    }
}

# Guruhda bir xil odam uchun ketma-ket spam bo'lmasligi uchun cooldown (20 soniya)
# (chat_id, target_user_id) -> float(timestamp)
_last_notified: dict[tuple[int, int], float] = {}


def is_sleep_allowed(user: types.User | None) -> bool:
    """Faqat @khojayev_ramz va @wdablyu uchun ruxsat."""
    if not user:
        return False
    if user.id in ALLOWED_SLEEP_USER_IDS:
        return True
    if user.username and user.username.lower() in ALLOWED_SLEEP_USERNAMES:
        return True
    return False


def parse_sleep_args(args_text: str) -> tuple[int | None, str | None]:
    """
    Vaqt va sababni ajratib olish.
    Qo'llab-quvvatlanadigan formatlar:
    - 1, 2 (birliksiz son kiritilsa -> soat deb hisoblanadi)
    - 1h, 2h, 30m, 45m, 1d
    - 1ч, 30м, 1д, 1 soat, 30 daqiqa, 1 kun
    - 1h darsdaman, 2 uxlayapman, 30m ovqatlanish
    """
    if not args_text or not args_text.strip():
        return None, None

    text = args_text.strip()
    pattern = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(h|m|d|s|w|mo|y|soat|daqiqa|kun|hafta|oy|yil|ч|м|д|с|hour|hours|min|minute|minutes|week|weeks|month|months|year|years)?\b',
        re.IGNORECASE
    )
    match = pattern.search(text)
    if not match:
        return None, None

    num = float(match.group(1))
    unit = (match.group(2) or "").lower()

    if not unit:
        seconds = int(num * 3600)  # Standart: soat
    elif unit in ("s", "с", "sec", "second", "seconds", "soniya", "sekund"):
        seconds = int(num)
    elif unit in ("m", "daqiqa", "м", "min", "minute", "minutes"):
        seconds = int(num * 60)
    elif unit in ("h", "soat", "ч", "hour", "hours"):
        seconds = int(num * 3600)
    elif unit in ("d", "kun", "д", "day", "days"):
        seconds = int(num * 86400)
    elif unit in ("w", "wk", "hafta", "week", "weeks", "нед"):
        seconds = int(num * 604800)
    elif unit in ("mo", "oy", "month", "months", "мес"):
        seconds = int(num * 2592000)
    elif unit in ("y", "yr", "yil", "year", "years", "г", "год"):
        seconds = int(num * 31536000)
    else:
        seconds = int(num * 3600)

    # Sababni qirqib olish (vaqtdan tashqari qolgan matn)
    reason = text[:match.start()] + text[match.end():]
    reason = reason.strip()
    reason = re.sub(r'\s+', ' ', reason)

    return seconds, (reason if reason else None)


def format_sleep_info(sleep_data: dict) -> str:
    """Uyqudagi foydalanuvchi haqida chiroyli xabar tayyorlash."""
    sleep_until = sleep_data["sleep_until"]
    now_utc = datetime.now(timezone.utc)
    remaining_seconds = max(0, int((sleep_until - now_utc).total_seconds()))

    if remaining_seconds >= 86400:
        days = remaining_seconds // 86400
        hours = (remaining_seconds % 86400) // 3600
        remaining_str = f"{days} kun {hours} soat" if hours else f"{days} kun"
    elif remaining_seconds >= 3600:
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        remaining_str = f"{hours} soat {minutes} daqiqa" if minutes else f"{hours} soat"
    else:
        minutes = max(1, remaining_seconds // 60)
        remaining_str = f"{minutes} daqiqa"

    target_uz = sleep_until.astimezone(TASHKENT_TZ)
    now_uz = now_utc.astimezone(TASHKENT_TZ)

    if target_uz.date() == now_uz.date():
        time_str = f"soat {target_uz.strftime('%H:%M')} da"
    elif target_uz.date() == (now_uz + timedelta(days=1)).date():
        time_str = f"ertaga soat {target_uz.strftime('%H:%M')} da"
    else:
        time_str = f"{target_uz.strftime('%d.%m.%Y')} soat {target_uz.strftime('%H:%M')} da"

    name = sleep_data.get("full_name") or "Foydalanuvchi"
    reason = sleep_data.get("reason")

    msg = (
        f"😴 <b>{escape(name)}</b> hozir online emas (uyquda / band).\n"
        f"⏰ <b>Taxminiy qaytish vaqti:</b> {time_str} ({remaining_str} qoldi)."
    )
    if reason:
        msg += f"\n📝 <b>Sabab:</b> <i>{escape(reason)}</i>"

    return msg


SLEEP_COMMAND_REGEX = re.compile(r"^/(sleep|afk|uyqu|uxlash|сон|афк)\b", re.IGNORECASE)
WAKE_COMMAND_REGEX = re.compile(r"^/(wake|online|uygondim|проснулся)\b", re.IGNORECASE)


@router.message(lambda msg: bool(SLEEP_COMMAND_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_sleep(message: types.Message):
    if not is_sleep_allowed(message.from_user):
        return

    text = (message.text or message.caption or "").strip()
    # Buyruqdan keyingi qismni olish
    parts = text.split(maxsplit=1)
    args_text = parts[1] if len(parts) > 1 else ""

    duration_seconds, reason = parse_sleep_args(args_text)
    if not duration_seconds or duration_seconds <= 0:
        await message.reply(
            "ℹ️ <b>Uyqu / bandlik rejimini o'rnatish:</b>\n"
            "<code>/sleep &lt;vaqt&gt; [sabab]</code>\n\n"
            "<b>Misollar:</b>\n"
            "• <code>/sleep 1h</code> (1 soatga)\n"
            "• <code>/sleep 2</code> (2 soatga)\n"
            "• <code>/sleep 30m darsdaman</code> (30 daqiqaga, sababi bilan)\n"
            "• <code>/sleep 45m uxlayapman</code>\n"
            "• <code>/sleep 1d safardaman</code>",
            parse_mode="HTML"
        )
        return

    # Foydalanuvchini bazaga saqlash
    display_name = message.from_user.full_name
    if message.from_user.id in TRACKED_SLEEP_USERS:
        display_name = TRACKED_SLEEP_USERS[message.from_user.id]["display_name"]

    sleep_until = set_user_sleep(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=display_name,
        duration_seconds=duration_seconds,
        reason=reason
    )

    sleep_data = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "full_name": display_name,
        "sleep_until": sleep_until,
        "reason": reason
    }
    info_text = format_sleep_info(sleep_data)
    await message.reply(
        f"✅ <b>Uyqu / bandlik rejimi yoqildi!</b>\n\n"
        f"{info_text}\n\n"
        f"<i>Guruhga xabar yozganingizda yoki <code>/wake</code> buyrug'i orqali rejim avtomatik yakunlanadi.</i>",
        parse_mode="HTML"
    )


@router.message(lambda msg: bool(WAKE_COMMAND_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_wake(message: types.Message):
    if not is_sleep_allowed(message.from_user):
        return

    active_sleep = get_user_sleep(message.from_user.id)
    if active_sleep:
        remove_user_sleep(message.from_user.id)
        await message.reply("✅ <b>Uyqu / bandlik rejimi o'chirildi! Xush kelibsiz!</b>", parse_mode="HTML")
    else:
        await message.reply("ℹ️ Sizda faol uyqu rejimi yo'q edi.", parse_mode="HTML")


def is_sleep_mention_or_sleeping_user(message: types.Message) -> bool:
    """Faqat xabar uyqudagi foydalanuvchiga tegishli bo'lsagina True qaytaradi."""
    if not message.from_user or message.from_user.is_bot:
        return False

    # 1. Agar xabar yozgan odamning o'zi uyquda bo'lsa
    if get_user_sleep(message.from_user.id):
        return True

    text = (message.text or message.caption or "").strip()
    if text.startswith("/"):
        return False

    # 2. Reply qilingan bo'lsa
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id in ALLOWED_SLEEP_USER_IDS:
            return True

    # 3. Mention entity
    entities = message.entities or message.caption_entities or []
    for ent in entities:
        if ent.type == "mention":
            mention_username = text[ent.offset:ent.offset + ent.length].lstrip("@").lower()
            if mention_username in ALLOWED_SLEEP_USERNAMES:
                return True
        elif ent.type == "text_mention" and ent.user:
            if ent.user.id in ALLOWED_SLEEP_USER_IDS:
                return True

    # 4. Kalit so'zlar
    if text:
        for data in TRACKED_SLEEP_USERS.values():
            if data["regex"].search(text):
                return True

    return False


@router.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]), is_sleep_mention_or_sleeping_user)
async def check_sleep_mentions(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = (message.text or message.caption or "").strip()

    try:
        from group_bot.database import is_bot_enabled
    except ImportError:
        from database import is_bot_enabled
    if not is_bot_enabled(chat_id):
        return

    # 1. Agar xabar yozgan odamning o'zi uyquda bo'lsa -> avtomatik uyg'otamiz!
    active_sleep = get_user_sleep(user_id)
    if active_sleep:
        remove_user_sleep(user_id)
        display_name = active_sleep.get("full_name") or message.from_user.full_name
        await message.reply(
            f"👋 Xush kelibsiz, <b>{escape(display_name)}</b>! Uyqu / bandlik rejimi yakunlandi.",
            parse_mode="HTML"
        )
        # O'zi uyg'ongani haqida ma'lumot berildi, boshqa tekshiruvga hojat yo'q
        return

    # Agar boshqa slash buyruq bo'lsa, chat xabari sifatida tekshirmaymiz
    if text.startswith("/"):
        return

    # 2. Xabarda uyqudagi odamlarni qidirish (Reply, Mention, Ism/Kalit so'z)
    now_ts = time.time()
    target_user_ids = set()

    # A) Reply qilingan bo'lsa
    if message.reply_to_message and message.reply_to_message.from_user and not message.reply_to_message.from_user.is_bot:
        reply_user_id = message.reply_to_message.from_user.id
        if reply_user_id != user_id and reply_user_id in ALLOWED_SLEEP_USER_IDS:
            target_user_ids.add(reply_user_id)

    # B) Entity orqali mention qilingan bo'lsa
    entities = message.entities or message.caption_entities or []
    for ent in entities:
        if ent.type == "mention":
            mention_username = text[ent.offset:ent.offset + ent.length].lstrip("@").lower()
            for uid, data in TRACKED_SLEEP_USERS.items():
                if data["canonical_username"] == mention_username:
                    if uid != user_id:
                        target_user_ids.add(uid)
        elif ent.type == "text_mention" and ent.user:
            if ent.user.id != user_id and ent.user.id in ALLOWED_SLEEP_USER_IDS:
                target_user_ids.add(ent.user.id)

    # C) 2 ta maxsus foydalanuvchi uchun matnli kalit so'zlar (Lotin va Kirill)
    if text:
        for uid, data in TRACKED_SLEEP_USERS.items():
            if uid != user_id and data["regex"].search(text):
                target_user_ids.add(uid)

    # Agar hech kim topilmasa, bot jim turadi
    if not target_user_ids:
        return

    for target_id in target_user_ids:
        sleep_data = get_user_sleep(target_id)
        if not sleep_data:
            # Rejim o'rnatilmagan yoki vaqti o'tib ketgan bo'lsa -> mutlaqo jim turadi
            continue

        # Spamdan himoya (har 20 soniyada bir marta)
        cooldown_key = (chat_id, target_id)
        if now_ts - _last_notified.get(cooldown_key, 0.0) < 20.0:
            continue

        _last_notified[cooldown_key] = now_ts

        if target_id in TRACKED_SLEEP_USERS:
            sleep_data["full_name"] = TRACKED_SLEEP_USERS[target_id]["display_name"]

        response_text = format_sleep_info(sleep_data)
        await message.reply(response_text, parse_mode="HTML")
        break
