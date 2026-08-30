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

from bot.config import BOT_TOKEN, validate_config, GEMINI_API_KEYS
from bot.handlers import start, analyze

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot):
    """Sets up the bot menu commands in Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish / Start"),
        BotCommand(command="lang", description="🌐 Tilni tanlash / Change Language"),
        BotCommand(command="help", description="💡 Yordam / Help / Помощь"),
        BotCommand(command="about", description="ℹ️ Bot haqida / About"),
    ]
    await bot.set_my_commands(commands)


async def health_check_handler(request):
    """Health check endpoint for Render/Cloud platforms."""
    return web.json_response({
        "status": "online",
        "service": "AI FilmFinder Bot",
        "version": "2.0 Multi-Lang"
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
    """Main application entry point."""
    logger.info("🚀 AI Movie Finder Bot ishga tushirilmoqda (Multi-Language 2.0)...")

    # Check configuration
    errors = validate_config()
    if errors:
        for err in errors:
            logger.error(f"❌ Sozlama xatosi: {err}")
        logger.warning("Iltimos, .env faylini to'ldiring va qayta ishga tushiring.")
        return

    logger.info(f"🔑 Yuklangan Gemini API kalitlari soni: {len(GEMINI_API_KEYS)} ta (Auto-Rotation faol)")

    # If running on Render or any cloud with $PORT set, start background health server
    port = os.getenv("PORT")
    if port:
        try:
            await start_web_server(int(port))
        except Exception as e:
            logger.warning(f"[Web Server Warning] Port {port} da web server ishga tushmadi: {e}")

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Register handlers
    dp.include_router(start.router)
    dp.include_router(analyze.router)

    # Set command menu
    await set_bot_commands(bot)

    # Get bot info
    me = await bot.get_me()
    logger.info(f"✅ Bot muvaffaqiyatli ulandi: @{me.username} ({me.first_name})")

    # Delete existing webhook to enable polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🎬 Bot xabarlarni qabul qilishga tayyor! (Long-polling boshlandi)")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi.")
