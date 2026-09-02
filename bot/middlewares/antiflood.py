import time
import logging
from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class AntiFloodMiddleware(BaseMiddleware):
    """
    Sliding-window rate limiter protecting bot against flood attacks,
    rapid media spam, and server CPU exhaustion.
    """
    def __init__(self, limit_seconds: float = 1.0, max_requests_per_window: int = 4, window_seconds: float = 6.0):
        super().__init__()
        self.limit_seconds = limit_seconds
        self.max_requests = max_requests_per_window
        self.window_seconds = window_seconds
        self.user_history: Dict[int, list] = {}
        self.user_warned: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        user_id = user.id
        now = time.time()

        # Clean old timestamps
        timestamps = [t for t in self.user_history.get(user_id, []) if now - t < self.window_seconds]
        timestamps.append(now)
        self.user_history[user_id] = timestamps

        if len(timestamps) > self.max_requests:
            last_warn = self.user_warned.get(user_id, 0)
            if now - last_warn > 5.0:  # Warn once every 5 seconds
                self.user_warned[user_id] = now
                warning_text = (
                    "⏳ <b>Xabarlar juda tez yuborilmoqda!</b>\n\n"
                    "Iltimos, server xavfsizligi va barqarorligi uchun <b>bir necha soniya</b> kuting."
                )
                if isinstance(event, Message):
                    try:
                        await event.answer(warning_text, parse_mode="HTML")
                    except Exception:
                        pass
                elif isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⏳ Iltimos, shoshilmang! Biroz kuting.", show_alert=True)
                    except Exception:
                        pass
            return  # Drop spam request

        return await handler(event, data)
