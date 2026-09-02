import os
import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from bot.config import BOT_TOKEN, ADMIN_BOT_TOKEN, validate_config, GEMINI_API_KEYS, GROQ_API_KEYS
from bot.handlers import start, analyze, watchlist, quiz, actor, character_chat, inline_mode, history
from bot.middlewares.antiflood import AntiFloodMiddleware
from bot.services.backup import start_cloud_backup_scheduler
from admin_bot import handlers as admin_handlers

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def set_main_bot_commands(bot: Bot):
    """Sets up rich menu commands for Main Bot."""
    commands = [
        BotCommand(command="start", description="🚀 Boshlash / Start"),
        BotCommand(command="random", description="🎲 AI Kino Tanlash / Mood Curator"),
        BotCommand(command="character", description="🎭 Qahramonlar bilan suhbat"),
        BotCommand(command="actor", description="⭐️ Aktyor / Rejissyor filmlari"),
        BotCommand(command="saved", description="❤️ Saqlanganlar / Watchlist"),
        BotCommand(command="history", description="📂 Qidiruv tarixi / Search history"),
        BotCommand(command="invite", description="👥 Do'stlarni taklif qilish / Referral"),
        BotCommand(command="quiz", description="🎮 AI Kino Viktorinasi / Quiz"),
        BotCommand(command="alerts", description="🔔 Premyera eslatmalari"),
        BotCommand(command="lang", description="🌐 Tilni tanlash / Language"),
        BotCommand(command="help", description="💡 Yordam / Help"),
        BotCommand(command="about", description="ℹ️ Bot haqida / About"),
    ]
    await bot.set_my_commands(commands)


async def set_admin_bot_commands(bot: Bot):
    """Sets up the bot menu commands for Admin Bot."""
    commands = [
        BotCommand(command="start", description="👑 Boshqaruv Markazi / Dashboard"),
        BotCommand(command="cancel", description="❌ Jarayonni bekor qilish"),
    ]
    await bot.set_my_commands(commands)


async def health_check_handler(request):
    """Health check endpoint for Render/Cloud platforms."""
    return web.json_response({
        "status": "online",
        "service": "AI FilmFinder Super Multi-Bot Cluster",
        "version": "3.5 Master AI Edition",
        "gemini_keys": len(GEMINI_API_KEYS),
        "groq_keys": len(GROQ_API_KEYS)
    })


async def start_web_server(port: int):
    """Starts a minimal HTTP web server for Render health checks."""
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 Cloud Health-Check Web Server ishga tushdi (Port: {port})")


async def main():
    """Main cluster entry point."""
    logger.info("🚀 AI Movie Finder Bot Cluster 3.5 ishga tushirilmoqda...")

    # Check configuration
    errors = validate_config()
    if errors:
        for err in errors:
            logger.error(f"❌ Sozlama xatosi: {err}")
        return

    logger.info(f"🔑 Gemini Kalitlar: {len(GEMINI_API_KEYS)} ta | Groq Kalitlar: {len(GROQ_API_KEYS)} ta")

    # Start background health server if PORT is defined (Render.com)
    port = os.getenv("PORT")
    if port:
        try:
            await start_web_server(int(port))
        except Exception as e:
            logger.warning(f"[Web Server Warning] Port {port} da web server ishga tushmadi: {e}")

    # 1. Initialize Main Search Bot
    main_bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    main_dp = Dispatcher()

    # Rate limiting & Anti-flood protection shield
    main_dp.message.middleware(AntiFloodMiddleware(max_requests_per_window=5, window_seconds=6.0))
    main_dp.callback_query.middleware(AntiFloodMiddleware(max_requests_per_window=6, window_seconds=6.0))

    main_dp.include_router(start.router)
    main_dp.include_router(character_chat.router)
    main_dp.include_router(actor.router)
    main_dp.include_router(watchlist.router)
    main_dp.include_router(quiz.router)
    main_dp.include_router(history.router)
    main_dp.include_router(inline_mode.router)
    main_dp.include_router(analyze.router)
    await set_main_bot_commands(main_bot)
    await main_bot.delete_webhook(drop_pending_updates=False)

    main_me = await main_bot.get_me()
    logger.info(f"✅ Asosiy qidiruv boti ulandi: @{main_me.username} ({main_me.first_name})")

    polling_tasks = [
        main_dp.start_polling(main_bot),
        start_cloud_backup_scheduler()
    ]

    # 2. Initialize Dedicated Admin Bot
    admin_bot = None
    if ADMIN_BOT_TOKEN:
        try:
            admin_bot = Bot(
                token=ADMIN_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            admin_dp = Dispatcher()
            admin_dp.include_router(admin_handlers.router)
            await set_admin_bot_commands(admin_bot)
            await admin_bot.delete_webhook(drop_pending_updates=False)

            admin_me = await admin_bot.get_me()
            logger.info(f"👑 Maxsus Admin Boti ulandi: @{admin_me.username} ({admin_me.first_name})")
            polling_tasks.append(admin_dp.start_polling(admin_bot))
        except Exception as e:
            logger.error(f"❌ Admin Botni ishga tushirishda xatolik: {e}")

    logger.info("🎬 Barcha botlar 24/7 rejimda to'liq ishga tushdi!")

    try:
        await asyncio.gather(*polling_tasks)
    finally:
        await main_bot.session.close()
        if admin_bot:
            await admin_bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Botlar to'xtatildi.")
