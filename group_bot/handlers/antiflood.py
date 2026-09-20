import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import Message, TelegramObject, ChatPermissions
from aiogram.exceptions import TelegramBadRequest

from database import delete_flood_messages

# Sozlamalar:
# 1. Stiker, GIF va Premium emoji uchun:
MEDIA_WINDOW = 4.0        # Tezkor: 4s ichida 2 ta bo'lsa
MEDIA_LIMIT = 2
MEDIA_LONG_WINDOW = 60.0  # Sekin flood: 60s ichida 4 ta bo'lsa
MEDIA_LONG_LIMIT = 4

# 2. '/' belgisi bilan yozilgan xabarlar uchun: 5 tadan ko'p bo'lsa (1m mute)
SLASH_WINDOW = 5.0   # soniya
SLASH_LIMIT = 5

# 3. Oddiy matnli xabarlar (flood) uchun: 4 ta bo'lsa (30 sekund mute)
TEXT_WINDOW = 5.0    # soniya
TEXT_LIMIT = 4
MULTILINE_LIMIT = 4  # Bitta xabarda 4+ qator bo'lib ekranni egallasa

# Foydalanuvchilar tarixi: (chat_id, user_id) -> list[(timestamp, message_id)]
_media_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_media_long_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_slash_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_text_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)


async def is_telegram_admin(chat_id: int, user_id: int, bot: Bot) -> bool:
    """Foydalanuvchi guruh admini yoki egasi ekanligini aniqlash."""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        return False


def is_media_or_emoji(message: Message) -> bool:
    """Stiker, GIF yoki Telegram Premium emoji borligini aniqlash."""
    if message.sticker or message.animation:
        return True

    entities = message.entities or message.caption_entities or []
    for entity in entities:
        if entity.type == "custom_emoji":
            return True

    return False


def is_slash_command(message: Message) -> bool:
    """Xabar '/' belgisi bilan boshlanganini aniqlash."""
    text = (message.text or message.caption or "").strip()
    if text.startswith("/"):
        return True

    entities = message.entities or message.caption_entities or []
    for entity in entities:
        if entity.type == "bot_command":
            return True

    return False


async def handle_flood_action(
    event: Message,
    bot: Bot,
    is_admin_user: bool,
    msg_ids: list[int],
    duration: timedelta,
    reason: str
):
    """
    Flood sodir bo'lganda:
    - Xabarlarni Telegramdan o'chirish.
    - Xabarlarni statadan (bazadan) tozalash.
    - Agar ADMIN bo'lsa: @wdablyu nomidan ogohlantirish berish.
    - Agar ODDIY a'zo bo'lsa: Mute qilish va bildirishnoma berish.
    """
    # 1. Flood paytidagi barcha xabarlarni Telegramdan o'chirish
    for m_id in set(msg_ids):
        try:
            await bot.delete_message(chat_id=event.chat.id, message_id=m_id)
        except TelegramBadRequest:
            pass

    # 2. Ushbu xabarlarni statadan (bazadan) o'chirish
    delete_flood_messages(event.chat.id, event.from_user.id, msg_ids)

    # 3. Agar foydalanuvchi ADMIN bo'lsa:
    if is_admin_user:
        admin_name = f"@{event.from_user.username}" if event.from_user.username else escape(event.from_user.full_name)
        warning_text = (
            f"⚠️ <b>Hurmatli {admin_name}</b> agar yana flood qilishni to'xtatmasangiz "
            "adminlikdan olinasiz yoki owner @wdablyu tomonidan jazolanasiz!"
        )
        try:
            await bot.send_message(
                chat_id=event.chat.id,
                text=warning_text,
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass
        return

    # 4. Agar ODDIY a'zo bo'lsa: Mute berish
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
            chat_id=event.chat.id,
            user_id=event.from_user.id,
            permissions=permissions,
            until_date=until_date
        )

        seconds = int(duration.total_seconds())
        dur_text = "1 daqiqaga" if seconds >= 60 else "30 soniyaga"

        await bot.send_message(
            chat_id=event.chat.id,
            text=f"⚠️ <b>{escape(event.from_user.full_name)}</b>, {reason} uchun <b>{dur_text} mute</b> qilindingiz va flood xabarlaringiz o'chirildi!",
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


class AntiFloodMiddleware(BaseMiddleware):
    """
    Qoida 2 bo'yicha Anti-Flood:
    - Oddiy a'zolar: xabarlar o'chiriladi, statadan o'chadi va mute beriladi.
    - Adminlar: xabarlar o'chiriladi, statadan o'chadi va @wdablyu nomidan ogohlantirish beriladi.
    - Owner (@wdablyu): to'liq daxlsiz.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user or event.from_user.is_bot:
            return await handler(event, data)

        if event.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            return await handler(event, data)

        bot: Bot = data["bot"]
        user = event.from_user

        # Guruh egasi / bosh admin (@wdablyu) flood uchun tekshirilmaydi
        if user.username and user.username.lower() == "wdablyu":
            return await handler(event, data)

        is_admin_user = await is_telegram_admin(event.chat.id, user.id, bot)

        now = time.time()
        key = (event.chat.id, user.id)

        # 1. Stiker, GIF, Premium Emoji tekshiruvi:
        # a) Tezkor flood: 4s ichida 2 ta
        # b) Sekin flood: 60s ichida 4 ta
        if is_media_or_emoji(event):
            history = [(t, m_id) for (t, m_id) in _media_history[key] if now - t <= MEDIA_WINDOW]
            history.append((now, event.message_id))
            _media_history[key] = history

            long_history = [(t, m_id) for (t, m_id) in _media_long_history[key] if now - t <= MEDIA_LONG_WINDOW]
            long_history.append((now, event.message_id))
            _media_long_history[key] = long_history

            # Tezkor (2 ta) yoki Sekin (1 daqiqada 4 ta) stiker flood aniqlansa:
            if len(history) >= MEDIA_LIMIT or len(long_history) >= MEDIA_LONG_LIMIT:
                msg_ids = list(set([m_id for (_, m_id) in history] + [m_id for (_, m_id) in long_history]))
                _media_history[key] = []
                _media_long_history[key] = []
                _slash_history[key] = []
                _text_history[key] = []
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=msg_ids,
                    duration=timedelta(minutes=1),
                    reason="me'yordan ortiq stiker yoki GIF yuborganingiz"
                )
                return

        # 2. '/' belgisi bilan yozilgan xabarlar tekshiruvi (5 ta)
        elif is_slash_command(event):
            history = [(t, m_id) for (t, m_id) in _slash_history[key] if now - t <= SLASH_WINDOW]
            history.append((now, event.message_id))
            _slash_history[key] = history

            if len(history) >= SLASH_LIMIT:
                msg_ids = [m_id for (_, m_id) in history]
                _media_history[key] = []
                _slash_history[key] = []
                _text_history[key] = []
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=msg_ids,
                    duration=timedelta(minutes=1),
                    reason="ketma-ket '/' belgisi bilan xabarlar yuborganingiz"
                )
                return

        # 3. Oddiy matnli xabarlar flood tekshiruvi (4 ta yoki ko'p qatorli spam)
        else:
            text = (event.text or event.caption or "").strip()

            # Agar bitta xabarning o'zida 4+ qatorli keraksiz matn bo'lsa:
            if text.count("\n") >= MULTILINE_LIMIT:
                _media_history[key] = []
                _slash_history[key] = []
                _text_history[key] = []
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=[event.message_id],
                    duration=timedelta(seconds=35),
                    reason="ko'p qatorli matn bilan flood qilganingiz"
                )
                return

            history = [(t, m_id) for (t, m_id) in _text_history[key] if now - t <= TEXT_WINDOW]
            history.append((now, event.message_id))
            _text_history[key] = history

            if len(history) >= TEXT_LIMIT:
                msg_ids = [m_id for (_, m_id) in history]
                _media_history[key] = []
                _slash_history[key] = []
                _text_history[key] = []
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=msg_ids,
                    duration=timedelta(seconds=35),
                    reason="ketma-ket xabarlar yuborib flood qilganingiz"
                )
                return

        return await handler(event, data)
