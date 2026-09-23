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
    """Bot guruhga qo'shilganda yoki huquqlari o'zgarganda guruhni to'liq bazaga saqlash."""
    chat = event.chat
    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        from group_bot.database import save_chat_full_info, set_bot_status, record_chat_authorized_user
        from group_bot.bot import WEBAPP_URL

        new_status = event.new_chat_member.status
        old_status = event.old_chat_member.status

        added_by = event.from_user
        added_by_id = added_by.id if added_by else None
        added_by_name = added_by.full_name if added_by else None
        added_by_uname = added_by.username if added_by else None

        # A'zolar sonini aniqlash
        members_count = 0
        try:
            members_count = await bot.get_chat_member_count(chat.id)
        except Exception:
            pass

        # Guruh silkasi (ommaviy username yoki invite link)
        invite_link = None
        if chat.username:
            invite_link = f"https://t.me/{chat.username}"
        elif chat.invite_link:
            invite_link = chat.invite_link
        else:
            try:
                invite_link = await bot.export_chat_invite_link(chat.id)
            except Exception:
                pass

        if new_status in ("left", "kicked"):
            set_bot_status(chat.id, False)
        elif new_status in ("member", "administrator"):
            set_bot_status(chat.id, True)

        save_chat_full_info(
            chat_id=chat.id,
            title=chat.title or f"Guruh {chat.id}",
            username=chat.username,
            invite_link=invite_link,
            members_count=members_count,
            added_by_user_id=added_by_id,
            added_by_name=added_by_name,
            added_by_username=added_by_uname,
            bot_status=new_status
        )

        if added_by_id:
            record_chat_authorized_user(chat.id, added_by_id, is_admin=True)

        if new_status in ("member", "administrator") and old_status in ("left", "kicked"):
            # 1. Bot egasi (@khojayev_ramz) ga zudlik bilan hisobot yuborish
            owner_alert = (
                f"🎉 <b>YANGI GURUH QO‘SHILDI!</b> 🚀\n\n"
                f"👥 <b>Guruh:</b> <b>{escape(chat.title or 'Nomsiz')}</b>\n"
                f"🆔 <b>Chat ID:</b> <code>{chat.id}</code>\n"
                f"🔗 <b>Silka:</b> {invite_link or 'Mavjud emas (yopiq)'}\n"
                f"👥 <b>A’zolar soni:</b> {members_count} ta\n"
                f"👤 <b>Qo‘shgan:</b> {escape(added_by_name or 'Noma’lum')} "
                f"({f'@{added_by_uname}' if added_by_uname else 'usernamesiz'}) [ID: <code>{added_by_id}</code>]\n"
                f"🛡 <b>Bot maqomi:</b> {new_status.capitalize()}"
            )
            try:
                await bot.send_message(chat_id=8594505572, text=owner_alert, parse_mode="HTML")
            except Exception:
                pass

            # 2. Guruhga xush kelibsiz xabari
            try:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

                user_id_param = f"&user_id={added_by_id}" if added_by_id else ""
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="⚙️ Guruhni Sozlash (Mini App)",
                                web_app=WebAppInfo(url=f"{WEBAPP_URL}?chat_id={chat.id}{user_id_param}")
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
