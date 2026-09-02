import asyncio
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from aiogram import Bot
from aiogram.types import FSInputFile

from bot.config import ADMIN_BOT_TOKEN
from bot.services.db import DB_PATH, get_admin_setting, get_stats

logger = logging.getLogger(__name__)


async def send_database_backup():
    """Generates a compressed SQLite backup and sends it to Admin via Telegram."""
    if not ADMIN_BOT_TOKEN:
        return
    admin_chat_id = get_admin_setting("admin_chat_id", "")
    if not admin_chat_id or not DB_PATH.exists():
        return

    backup_bot = None
    zip_path = DB_PATH.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    try:
        # Create compressed zip
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(DB_PATH, arcname="users.db")

        stats = get_stats()
        caption = (
            "☁️ <b>AVTOMATIK KUNLIK BAZA ZAXIRASI (Daily Cloud Backup)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Sana:</b> <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
            f"👥 <b>Foydalanuvchilar:</b> <code>{stats.get('total_users', 0)} ta</code>\n"
            f"🔍 <b>Jami Qidiruvlar:</b> <code>{stats.get('total_searches', 0)} ta</code>\n"
            f"💾 <b>Hajmi:</b> <code>{zip_path.stat().st_size / 1024:.1f} KB</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <i>Barcha ma'lumotlar to'liq va xavfsiz saqlandi.</i>"
        )

        backup_bot = Bot(token=ADMIN_BOT_TOKEN)
        input_file = FSInputFile(str(zip_path), filename=zip_path.name)
        await backup_bot.send_document(chat_id=int(admin_chat_id), document=input_file, caption=caption, parse_mode="HTML")
        logger.info("[Cloud Backup] Daily database backup dispatched successfully to Admin.")
    except Exception as e:
        logger.error(f"[Cloud Backup Error] {e}")
    finally:
        if backup_bot:
            await backup_bot.session.close()
        if zip_path.exists():
            try:
                zip_path.unlink()
            except Exception:
                pass


async def start_cloud_backup_scheduler():
    """Daily backup scheduler task (runs every 24 hours in background)."""
    # Wait 60 seconds after boot before first check
    await asyncio.sleep(60)
    while True:
        try:
            await send_database_backup()
        except Exception as e:
            logger.error(f"[Backup Scheduler Error] {e}")
        # Sleep 24 hours (86400 seconds)
        await asyncio.sleep(86400)
