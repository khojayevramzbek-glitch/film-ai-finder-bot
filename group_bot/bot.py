import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Awaitable

GROUP_BOT_DIR = Path(__file__).resolve().parent
if str(GROUP_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(GROUP_BOT_DIR))

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.enums import ParseMode, ChatType
from aiogram.types import Message, TelegramObject
from aiogram.client.default import DefaultBotProperties

from group_bot.config import BOT_TOKEN
from group_bot.database import (
    init_db, add_message, cleanup_old_messages, is_bot_enabled,
    save_chat_title, is_prank_user, delete_message_record,
    init_admin_virtual_mutes_cache, is_admin_virtually_muted
)
from group_bot.handlers import main_router
from group_bot.handlers.antiflood import AntiFloodMiddleware
from group_bot.handlers.censor import CensorMiddleware

WEBAPP_URL = "https://uchunrisk-film-ai-finder-bot.hf.space/gradio_api/webapp"


class MessageTrackerMiddleware(BaseMiddleware):
    """
    Guruhdagi har bir xabarni ma'lumotlar bazasiga yozib boruvchi middleware.
    Botlarning xabarlari hisobga olinmaydi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user and not event.from_user.is_bot:
            # Barcha xabarlar, stiker, emoji va GIFlar stataga hisoblanadi (faqat flood bo'lsa o'chiriladi)
            add_message(
                chat_id=event.chat.id,
                user_id=event.from_user.id,
                full_name=event.from_user.full_name,
                username=event.from_user.username,
                message_id=event.message_id
            )
            # Guruh nomini saqlab borish
            if event.chat and event.chat.title:
                save_chat_title(event.chat.id, event.chat.title)
        return await handler(event, data)



class BotStatusEnforcerMiddleware(BaseMiddleware):
    """
    Agar bot guruhda o'chirilgan (is_bot_enabled == False) bo'lsa:
    Faqat botni qayta yoqish buyruqlariga ruxsat beradi (/bot on, bot on, /blizkiy on, blizkiy on).
    Boshqa BARCHA xabarlar, buyruqlar va hodisalar uchun bot guruhda MUTLAQO TO'XTATILADI
    (hech qanday xabar yubormaydi, o'chirmaydi, mute qilmaydi, e'tibor bermaydi).
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.chat:
            if event.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                chat_id = event.chat.id
                if not is_bot_enabled(chat_id):
                    text = (event.text or event.caption or "").strip().lower()
                    # Faqat botni qayta yoqish buyrug'iga ruxsat beriladi
                    if any(text.startswith(cmd) for cmd in [
                        "/bot on", "bot on", "/blizkiy on", "blizkiy on",
                        "/bot yoq", "bot yoq", "/blizkiy yoq", "blizkiy yoq"
                    ]):
                        return await handler(event, data)
                    # Qolgan barcha holatlarda bot guruhda to'liq to'xtaydi (hech qanday ishlash bo'lmaydi)
                    return
        return await handler(event, data)


class PrankModeMiddleware(BaseMiddleware):
    """
    Hazil rejimi (Ghost / Prank Mode):
    Guruhdagi belgilangan a'zolar (maksimal 5 ta username) nima yozsa yoki
    qanday stiker, GIF, rasm, video, audio, ovozli xabar yuborsa, bot darhol
    o'chirib tashlaydi. Hatto foydalanuvchi guruh admini bo'lsa ham!
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.chat:
            if event.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                chat_id = event.chat.id
                if event.from_user:
                    uid = event.from_user.id
                    uname = (event.from_user.username or "").lower()
                    if uid in {8594505572, 7690283463} or uname in {"khojayev_ramz", "wdablyu"}:
                        return await handler(event, data)
                    if uname and is_prank_user(chat_id, uname):
                        try:
                            await event.delete()
                            delete_message_record(chat_id, event.message_id)
                        except Exception:
                            pass
                        # Xabar o'chirildi, boshqa ishlov beruvchilarga o'tkazilmaydi
                        return
        return await handler(event, data)


class AdminVirtualMuteMiddleware(BaseMiddleware):
    """
    Adminlar uchun «Virtual Mute»:
    Agar admin virtual mutedagi ro'yxatda bo'lsa, u yozgan har qanday
    xabar, stiker, GIF, rasm yoki media 0.1 soniya (chaqmoqdek tezlikda)
    o'chirib tashlanadi va statistika toza saqlanadi.
    Bot egalari mutlaqo daxlsiz.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.chat:
            if event.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
                if event.from_user:
                    uid = event.from_user.id
                    uname = (event.from_user.username or "").lower()
                    # Bot egalari daxlsiz
                    if uid in {8594505572, 7690283463} or uname in {"khojayev_ramz", "wdablyu"}:
                        return await handler(event, data)

                    if is_admin_virtually_muted(event.chat.id, uid):
                        try:
                            await event.delete()
                            delete_message_record(event.chat.id, event.message_id)
                        except Exception:
                            pass
                        return
        return await handler(event, data)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    logger.info("Ma'lumotlar bazasi tayyorlanmoqda...")
    init_db()
    cleanup_old_messages(days=3)
    init_admin_virtual_mutes_cache()

    logger.info("Bot ishga tushirilmoqda...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    # Bot umumiy holati: Agar bot o'chirilgan bo'lsa, guruhdagi barcha xabarlar va harakatlarni to'xtatadi
    dp.message.outer_middleware(BotStatusEnforcerMiddleware())
    # Hazil rejimi (Prank mode): ro'yxatdagi 5 ta a'zo nima yozsa bot darhol o'chiradi (admin bo'lsa ham)
    dp.message.outer_middleware(PrankModeMiddleware())
    # Adminlar uchun «Virtual Mute»: xabarlarni chaqmoqdek tezlikda (0.1s) o'chirish
    dp.message.outer_middleware(AdminVirtualMuteMiddleware())
    # Har bir xabarni hisobga oluvchi middleware qo'shish (statistika buzilmasligi uchun)
    dp.message.outer_middleware(MessageTrackerMiddleware())
    # So'kinish va haqorat filtri (Censor) - barcha xabarlardan oldin tekshiradi
    dp.message.outer_middleware(CensorMiddleware())
    # Qoida 2 bo'yicha Anti-Flood middleware (barcha xabar va stikerlarni tekshirish uchun outer_middleware)
    dp.message.outer_middleware(AntiFloodMiddleware())
    dp.include_router(main_router)

    # Navbatdagi xabarlarni saqlab qolish
    await bot.delete_webhook(drop_pending_updates=False)

    bot_info = await bot.get_me()
    logger.info(f"Bot faol: @{bot_info.username} ({bot_info.first_name}) [ID: {bot_info.id}]")

    # Faqat /start buyrug'ini qoldirish, qolgan barcha buyruqlarni Telegram menyusidan tozalash
    try:
        from aiogram.types import (
            BotCommand,
            BotCommandScopeDefault,
            BotCommandScopeAllPrivateChats,
            BotCommandScopeAllGroupChats,
            MenuButtonWebApp,
            WebAppInfo
        )
        # Default va Private chatlar uchun faqat /start
        await bot.set_my_commands(
            [BotCommand(command="start", description="🚀 Boshlash / Start")],
            scope=BotCommandScopeDefault()
        )
        await bot.set_my_commands(
            [BotCommand(command="start", description="🚀 Boshlash / Start")],
            scope=BotCommandScopeAllPrivateChats()
        )
        # Guruhlardagi / buyruqlar menyusini tozalash
        await bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())
        logger.info("🧹 Telegram buyruqlar menyusi tozalandi: Faqat /start qoldirildi.")

        # Chat menu tugmasini Telegram Mini App ga ulash
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📱 Boshqaruv",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
        logger.info(f"📱 Telegram Menu Button Mini App ga muvaffaqiyatli ulandi: {WEBAPP_URL}")
    except Exception as e:
        logger.warning(f"Menu button va buyruqlarni o'rnatishda xatolik: {e}")

    try:
        await dp.start_polling(

            bot,
            allowed_updates=["message", "chat_member", "my_chat_member", "callback_query"],
            handle_signals=False
        )
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
