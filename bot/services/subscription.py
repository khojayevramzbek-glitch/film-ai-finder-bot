import logging
from typing import List, Dict, Any, Tuple
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.db import get_active_channels
from bot.locales import get_msg

logger = logging.getLogger(__name__)


async def check_user_subscription(bot: Bot, user_id: int) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Checks if a user is subscribed to all active sponsor channels.
    Returns (is_subscribed: bool, missing_channels: List).
    """
    channels = get_active_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        ch_id = ch["channel_id"]
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                missing.append(ch)
        except Exception as e:
            # If bot is not admin in the channel or channel id is invalid
            logger.warning(f"[Subscription Check] Kanal {ch_id} tekshirilmadi: {e}")
            continue

    return len(missing) == 0, missing


def get_subscription_keyboard(missing_channels: List[Dict[str, Any]], lang: str = "uz") -> InlineKeyboardMarkup:
    """Generates inline buttons for sponsor channels and check button."""
    buttons = []
    for idx, ch in enumerate(missing_channels, 1):
        url = ch["channel_url"]
        title = ch["channel_title"] or f"Homiy Kanal #{idx}"
        buttons.append([InlineKeyboardButton(text=f"➕ {title}", url=url)])

    buttons.append([
        InlineKeyboardButton(text=get_msg(lang, "btn_check_sub"), callback_data="check_subscription")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
