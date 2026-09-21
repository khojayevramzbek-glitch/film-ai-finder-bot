import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.types import Message, TelegramObject, ChatPermissions
from aiogram.exceptions import TelegramBadRequest

try:
    from group_bot.database import delete_flood_messages, is_bot_enabled, get_chat_full_settings, format_duration
except ImportError:
    from database import delete_flood_messages, is_bot_enabled, get_chat_full_settings, format_duration

# Sozlamalar:
# 1. Stiker, GIF va Premium emoji uchun:
MEDIA_WINDOW = 4.0        # Tezkor: 4s ichida 2 ta bo'lsa
MEDIA_LIMIT = 2
MEDIA_LONG_WINDOW = 60.0  # Sekin flood: 60s ichida 4 ta bo'lsa
MEDIA_LONG_LIMIT = 4

# 2. '/' belgisi bilan yozilgan xabarlar uchun: 5 tadan ko'p bo'lsa (1m mute)
SLASH_WINDOW = 5.0   # soniya
SLASH_LIMIT = 5

# 3. Matnli xabarlar va bo'lak-bo'lak (salom, qales, yaxshimisz) flood:
TEXT_WINDOW = 5.0          # Tezkor: 5s ichida 4 ta bo'lsa
TEXT_LIMIT = 4
PIECE_FAST_WINDOW = 10.0   # 10s ichida 3 ta bo'lak xabar
PIECE_FAST_LIMIT = 3
PIECE_SLOW_WINDOW = 20.0   # 20s ichida 5 ta xabar
PIECE_SLOW_LIMIT = 5
MULTILINE_LIMIT = 4        # Bitta xabarda 4+ qator bo'lib ekranni egallasa

# Foydalanuvchilar tarixi: (chat_id, user_id) -> list[(timestamp, message_id)]
_media_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_media_long_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_slash_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_text_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_piece_fast_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)
_piece_slow_history: dict[tuple[int, int], list[tuple[float, int]]] = defaultdict(list)


async def delete_message_later(bot: Bot, chat_id: int, message_id: int, delay: int = 15):
    """Xabarni ma'lum vaqtdan so'ng chatdan avtomatik tozalash."""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


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
            f"⚠️ <b>Hurmatli {admin_name}</b>, guruhda bo‘lak-bo‘lak xabarlar yuborib flood qilmang!\n"
            f"Barcha yuborgan xabarlaringiz darhol o‘chirildi. Agar bu holat takrorlansa, owner @wdablyu tomonidan adminlikdan olinasiz!"
        )
        try:
            warn_msg = await bot.send_message(
                chat_id=event.chat.id,
                text=warning_text,
                parse_mode="HTML"
            )
            asyncio.create_task(delete_message_later(bot, event.chat.id, warn_msg.message_id, delay=15))
        except TelegramBadRequest:
            pass
        return

    # 4. Agar ODDIY a'zo bo'lsa: Mute berish
    seconds = int(duration.total_seconds())
    dur_text = format_duration(seconds)
    until_date = datetime.now(timezone.utc) + timedelta(seconds=max(seconds, 35))
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

        if seconds < 35:
            async def unmute_after(b: Bot, c_id: int, u_id: int, delay: int):
                await asyncio.sleep(delay)
                try:
                    p = ChatPermissions(
                        can_send_messages=True,
                        can_send_photos=True,
                        can_send_videos=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                    await b.restrict_chat_member(chat_id=c_id, user_id=u_id, permissions=p)
                except Exception:
                    pass
            asyncio.create_task(unmute_after(bot, event.chat.id, event.from_user.id, delay=seconds))

        await bot.send_message(
            chat_id=event.chat.id,
            text=f"⚠️ <b>{escape(event.from_user.full_name)}</b>, {reason} uchun <b>{dur_text}ga mute</b> qilindingiz va flood xabarlaringiz o'chirildi!",
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass


class AntiFloodMiddleware(BaseMiddleware):
    """
    Qoida 2 bo'yicha Anti-Flood:
    - Oddiy a'zolar: xabarlar o'chiriladi, statadan o'chadi va mute beriladi (Mini App sozlamalariga ko'ra).
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

        # Bot guruhda o'chirilgan (pauza) bo'lsa tekshirmaymiz
        if not is_bot_enabled(event.chat.id):
            return await handler(event, data)

        bot: Bot = data["bot"]
        user = event.from_user

        # Guruh egasi / bosh admin (@wdablyu) flood uchun tekshirilmaydi
        if user.username and user.username.lower() == "wdablyu":
            return await handler(event, data)

        is_admin_user = await is_telegram_admin(event.chat.id, user.id, bot)

        settings = get_chat_full_settings(event.chat.id)
        flood_sec = int(settings.get("flood_mute_seconds", 900))
        flood_duration = timedelta(seconds=flood_sec)

        media_limit = int(settings.get("flood_sticker_limit", 3))
        media_window = float(settings.get("flood_sticker_window", 4))

        msg_limit = int(settings.get("flood_msg_limit", 5))
        msg_window = float(settings.get("flood_msg_window", 4))

        now = time.time()
        key = (event.chat.id, user.id)

        # 1. Stiker, GIF, Premium Emoji tekshiruvi:
        if is_media_or_emoji(event):
            history = [(t, m_id) for (t, m_id) in _media_history[key] if now - t <= media_window]
            history.append((now, event.message_id))
            _media_history[key] = history

            long_history = [(t, m_id) for (t, m_id) in _media_long_history[key] if now - t <= MEDIA_LONG_WINDOW]
            long_history.append((now, event.message_id))
            _media_long_history[key] = long_history

            # Tezkor (media_limit ta) yoki Sekin (1 daqiqada 4 ta) stiker flood aniqlansa:
            if len(history) >= media_limit or len(long_history) >= MEDIA_LONG_LIMIT:
                msg_ids = list(set([m_id for (_, m_id) in history] + [m_id for (_, m_id) in long_history]))
                _media_history[key] = []
                _media_long_history[key] = []
                _slash_history[key] = []
                _text_history[key] = []
                _piece_fast_history[key] = []
                _piece_slow_history[key] = []
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=msg_ids,
                    duration=flood_duration,
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
                _piece_fast_history[key] = []
                _piece_slow_history[key] = []
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=msg_ids,
                    duration=flood_duration,
                    reason="ketma-ket '/' belgisi bilan xabarlar yuborganingiz"
                )
                return

        # 3. Oddiy matnli va bo'lak-bo'lak (salom, qales, yaxshimisz) flood tekshiruvi
        else:
            text = (event.text or event.caption or "").strip()

            # Agar bitta xabarning o'zida 4+ qatorli keraksiz matn bo'lsa:
            if text.count("\n") >= MULTILINE_LIMIT:
                _media_history[key] = []
                _slash_history[key] = []
                _text_history[key] = []
                _piece_fast_history[key] = []
                _piece_slow_history[key] = []
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=[event.message_id],
                    duration=flood_duration,
                    reason="ko'p qatorli matn bilan flood qilganingiz"
                )
                return

            # a) Tezkor flood: msg_window ichida msg_limit ta xabar
            history = [(t, m_id) for (t, m_id) in _text_history[key] if now - t <= msg_window]
            history.append((now, event.message_id))
            _text_history[key] = history

            # b) Bo'lak-bo'lak tezkor flood: 10s ichida 3 ta xabar (masalan: salom, qales, yaxshimisz)
            piece_fast = [(t, m_id) for (t, m_id) in _piece_fast_history[key] if now - t <= PIECE_FAST_WINDOW]
            piece_fast.append((now, event.message_id))
            _piece_fast_history[key] = piece_fast

            # c) Bo'lak-bo'lak sekin flood: 20s ichida 5 ta xabar
            piece_slow = [(t, m_id) for (t, m_id) in _piece_slow_history[key] if now - t <= PIECE_SLOW_WINDOW]
            piece_slow.append((now, event.message_id))
            _piece_slow_history[key] = piece_slow

            is_piece_flood = len(piece_fast) >= PIECE_FAST_LIMIT or len(piece_slow) >= PIECE_SLOW_LIMIT
            is_fast_flood = len(history) >= msg_limit

            if is_fast_flood or is_piece_flood:
                all_flood_ids = list(set(
                    [m_id for (_, m_id) in history] +
                    [m_id for (_, m_id) in piece_fast] +
                    [m_id for (_, m_id) in piece_slow]
                ))
                _media_history[key] = []
                _slash_history[key] = []
                _text_history[key] = []
                _piece_fast_history[key] = []
                _piece_slow_history[key] = []

                reason = "bo‘lak-bo‘lak qilib ketma-ket xabarlar yuborganingiz" if is_piece_flood else "ketma-ket xabarlar yuborib flood qilganingiz"
                await handle_flood_action(
                    event,
                    bot,
                    is_admin_user=is_admin_user,
                    msg_ids=all_flood_ids,
                    duration=flood_duration,
                    reason=reason
                )
                return

        return await handler(event, data)
