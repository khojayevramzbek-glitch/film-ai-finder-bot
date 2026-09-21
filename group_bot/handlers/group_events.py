import re
from html import escape
from aiogram import Router, types, F, Bot
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
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


@router.my_chat_member()
async def on_my_chat_member(event: types.ChatMemberUpdated, bot: Bot):
    """Bot guruhga qo'shilganda yoki huquqlari o'zgarganda guruhni bazaga saqlash."""
    chat = event.chat
    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        from group_bot.database import save_chat_title, set_bot_status
        from group_bot.bot import WEBAPP_URL

        save_chat_title(chat.id, chat.title or f"Guruh {chat.id}")

        new_status = event.new_chat_member.status
        old_status = event.old_chat_member.status

        if new_status in ("left", "kicked"):
            set_bot_status(chat.id, False)
        elif new_status in ("member", "administrator"):
            set_bot_status(chat.id, True)

        if new_status in ("member", "administrator") and old_status in ("left", "kicked"):
            try:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="⚙️ Guruhni Sozlash (Mini App)",
                                web_app=WebAppInfo(url=f"{WEBAPP_URL}?chat_id={chat.id}")
                            )
                        ]
                    ]
                )
                await bot.send_message(
                    chat_id=chat.id,
                    text=(
                        f"👋 <b>Assalomu alaykum, {escape(chat.title or 'Guruh')}!</b>\n\n"
                        "🛡 <b>Blizkiy Moderatsiya Boti</b> guruhingizga muvaffaqiyatli qo'shildi.\n"
                        "Bot to'liq ishlashi va guruhni himoya qilishi uchun unga <b>Administrator</b> huquqini bering.\n\n"
                        "⚙️ So'kinish jazosi, mute daqiqalari, toshqin chegaralari va qoidalarni o'zingizga moslash uchun "
                        "pastdagi tugmani bosing:"
                    ),
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception:
                pass
