import re
from html import escape
from aiogram import Router, types, F, Bot
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from .admin_commands import is_admin

router = Router()




STATA_CLEANUP_REGEX = re.compile(
    r"^\s*(/?[sс][tт][aа][tт][aа]?|[sс][tт][aа][tт][sс]?)\b",
    re.IGNORECASE
)


@router.message(lambda msg: bool(STATA_CLEANUP_REGEX.search((msg.text or msg.caption or "").strip())))
async def delete_stata_command(message: types.Message):
    """Statani buyrug'i guruhda yozilganda, uni darhol o'chirib tashlash."""
    try:
        await message.delete()
    except Exception:
        pass
