import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Awaitable

GROUP_BOT_DIR = Path(__file__).resolve().parent
if str(GROUP_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(GROUP_BOT_DIR))

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.types import Message, TelegramObject
from aiogram.client.default import DefaultBotProperties

from group_bot.config import BOT_TOKEN
from group_bot.database import init_db, add_message, cleanup_old_messages
from group_bot.handlers import main_router
from group_bot.handlers.antiflood import AntiFloodMiddleware


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

    logger.info("Bot ishga tushirilmoqda...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    # Har bir xabarni hisobga oluvchi middleware qo'shish
    dp.message.outer_middleware(MessageTrackerMiddleware())
    # Qoida 2 bo'yicha Anti-Flood middleware (barcha xabar va stikerlarni tekshirish uchun outer_middleware)
    dp.message.outer_middleware(AntiFloodMiddleware())
    dp.include_router(main_router)

    # Navbatdagi xabarlarni saqlab qolish
    await bot.delete_webhook(drop_pending_updates=False)

    bot_info = await bot.get_me()
    logger.info(f"Bot faol: @{bot_info.username} ({bot_info.first_name}) [ID: {bot_info.id}]")

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
