import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Awaitable

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

GROUP_BOT_DIR = Path(__file__).resolve().parent
if str(GROUP_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(GROUP_BOT_DIR))

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.enums import ParseMode, ChatType
from aiogram.types import Message, TelegramObject
from aiogram.client.default import DefaultBotProperties

from group_bot.config import BOT_TOKEN, get_webapp_url
from group_bot.database import (
    init_db, add_message, cleanup_old_messages, is_bot_enabled,
    save_chat_title, is_prank_user, delete_message_record,
    init_admin_virtual_mutes_cache, is_admin_virtually_muted
)
from group_bot.handlers import main_router
from group_bot.handlers.antiflood import AntiFloodMiddleware
from group_bot.handlers.censor import CensorMiddleware


class MessageTrackerMiddleware(BaseMiddleware):
    """
    Guruhdagi har bir xabarni ma'lumotlar bazasiga yozib boruvchi va log qiluvchi middleware.
    Botlarning xabarlari hisobga olinmaydi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.from_user and not event.from_user.is_bot:
            text_preview = (event.text or event.caption or "<media>")[:80]
            logging.getLogger("group_bot").info(
                f"💬 [GROUP {event.chat.id}] @{event.from_user.username or event.from_user.id} ({event.from_user.full_name}): {text_preview!r}"
            )
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
    Faqat botni qayta yoqish yoki holatini tekshirish buyruqlariga ruxsat beradi (/bot, /bot on, bot on va hk.).
    Boshqa BARCHA xabarlar, buyruqlar va hodisalar uchun bot guruhda MUTLAQO TO'XTATILADI.
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
                    # Botni tekshirish yoki qayta yoqish buyruqlariga ruxsat beriladi
                    if any(text.startswith(cmd) for cmd in [
                        "/bot", "bot", "/blizkiy", "blizkiy"
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
    # 1. Har bir xabarni hisobga oluvchi va log qiluvchi middleware (eng birinchi)
    dp.message.outer_middleware(MessageTrackerMiddleware())
    # 2. Bot umumiy holati: Agar bot o'chirilgan bo'lsa, xabarlarni to'xtatadi
    dp.message.outer_middleware(BotStatusEnforcerMiddleware())
    # 3. Hazil rejimi (Prank mode): ro'yxatdagi 5 ta a'zo xabarlarini o'chirish
    dp.message.outer_middleware(PrankModeMiddleware())
    # 4. Adminlar uchun «Virtual Mute»: xabarlarni chaqmoqdek tezlikda (0.1s) o'chirish
    dp.message.outer_middleware(AdminVirtualMuteMiddleware())
    # 5. So'kinish va haqorat filtri (Censor) - barcha xabarlardan oldin tekshiradi
    dp.message.outer_middleware(CensorMiddleware())
    # 6. Qoida 2 bo'yicha Anti-Flood middleware (barcha xabar va stikerlarni tekshirish uchun outer_middleware)
    dp.message.outer_middleware(AntiFloodMiddleware())
    dp.include_router(main_router)

    # Navbatdagi xabarlarni saqlab qolish
    await bot.delete_webhook(drop_pending_updates=False)

    bot_info = await bot.get_me()
    logger.info(f"Bot faol: @{bot_info.username} ({bot_info.first_name}) [ID: {bot_info.id}]")

    # 7. Ichki Mini App aiohttp veb-serverini ishga tushirish
    web_runner = None
    try:
        import os
        from aiohttp import web
        from group_bot.webapp_server import attach_aiohttp_routes
        app = web.Application()
        attach_aiohttp_routes(app)
        web_runner = web.AppRunner(app)
        await web_runner.setup()
        port = int(os.getenv("PORT", "7860"))
        site = web.TCPSite(web_runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"🌐 [Web Server] Mini App web server 0.0.0.0:{port} da muvaffaqiyatli ishga tushirildi.")
    except Exception as e:
        logger.warning(f"Web serverni ishga tushirishda ogohlantirish (ehtimol port band): {e}")

    # Telegram menyu buyruqlarini sozlash
    try:
        from aiogram.types import (
            BotCommand,
            BotCommandScopeDefault,
            BotCommandScopeAllPrivateChats,
            BotCommandScopeAllGroupChats,
            MenuButtonWebApp,
            WebAppInfo
        )
        # Default va Private chatlar uchun /start va /manager
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="🚀 Boshlash / Start"),
                BotCommand(command="manager", description="👑 Bot Menedjeri / Statistika"),
                BotCommand(command="help", description="💡 Yordam"),
            ],
            scope=BotCommandScopeDefault()
        )
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="🚀 Boshlash / Start"),
                BotCommand(command="manager", description="👑 Bot Menedjeri / Statistika"),
                BotCommand(command="help", description="💡 Yordam"),
            ],
            scope=BotCommandScopeAllPrivateChats()
        )
        # Guruhlar uchun to'liq buyruqlar menyusi
        group_commands = [
            BotCommand(command="start", description="🚀 Bot holatini tekshirish"),
            BotCommand(command="help", description="💡 Yordam va buyruqlar ro'yxati"),
            BotCommand(command="manager", description="👑 Bot Menedjer (Bot egasi)"),
            BotCommand(command="testwelcome", description="✨ Welcome kartasini sinash"),
            BotCommand(command="game", description="🎮 «Raqamni Top» dueli (game @user)"),
            BotCommand(command="topgame", description="🏆 O'yin reytingi va Gift sovg'alari"),
            BotCommand(command="gamestats", description="📊 Shaxsiy o'yin statistikangiz"),
            BotCommand(command="stata", description="📈 24 soatlik Top faol a'zolar"),
            BotCommand(command="rules", description="📜 Guruh qoidalarini ko'rish"),
            BotCommand(command="stopgame", description="🛑 Faol o'yinni to'xtatish"),
        ]
        await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        logger.info("📋 Telegram guruhlar menyusi buyruqlari muvaffaqiyatli yangilandi.")

        # Chat menu tugmasini Telegram Mini App ga ulash
        current_webapp_url = get_webapp_url()
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📱 Boshqaruv",
                web_app=WebAppInfo(url=current_webapp_url)
            )
        )
        logger.info(f"📱 Telegram Menu Button Mini App ga muvaffaqiyatli ulandi: {current_webapp_url}")
    except Exception as e:
        logger.warning(f"Menu button va buyruqlarni o'rnatishda xatolik: {e}")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "chat_member", "my_chat_member", "callback_query"],
            handle_signals=False
        )
    finally:
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
