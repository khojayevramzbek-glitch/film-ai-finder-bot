import os
import sys
import time
import re
import signal
import asyncio
import subprocess
import logging
from pathlib import Path

# Windows console UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from group_bot.config import get_webapp_url, set_webapp_url
import group_bot.bot as bot_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("launcher")


def start_cloudflared_tunnel(port: int = 7860):
    """
    Cloudflare Quick Tunnel (cloudflared.exe) orqali bepul va tezkor HTTPS tunnel ochadi.
    Telegram Mini App uchun to'liq HTTPS va iframe huquqlarini ta'minlaydi.
    """
    cloudflared_bin = ROOT_DIR / "cloudflared.exe"
    if not cloudflared_bin.exists():
        logger.warning(f"cloudflared.exe topilmadi. Mavjud URL ishlatiladi: {get_webapp_url()}")
        return None, None

    logger.info("⚡️ Cloudflare Tunnel ishga tushirilmoqda...")
    cmd = [str(cloudflared_bin), "tunnel", "--url", f"http://127.0.0.1:{port}"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    except Exception as e:
        logger.error(f"Cloudflared ishga tushirishda xatolik: {e}")
        return None, None

    tunnel_url = None
    start_time = time.time()
    # 20 soniya davomida Cloudflare tomonidan berilgan HTTPS domenini kutamiz
    while time.time() - start_time < 20:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        line_clean = line.strip()
        match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line_clean)
        if match:
            tunnel_url = match.group(0)
            break

    if tunnel_url:
        webapp_url = f"{tunnel_url}/webapp"
        logger.info(f"✅ Cloudflare Tunnel muvaffaqiyatli ochildi!")
        logger.info(f"🔗 Public URL: {tunnel_url}")
        logger.info(f"📱 Mini App URL: {webapp_url}")
        set_webapp_url(webapp_url)
        return proc, webapp_url
    else:
        logger.warning("Cloudflare Tunnel URL olinmadi. Mavjud URL qoladi.")
        return proc, None


def main():
    port = int(os.getenv("PORT", "7860"))
    cf_proc, active_webapp_url = start_cloudflared_tunnel(port=port)

    try:
        asyncio.run(bot_module.main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
    finally:
        if cf_proc:
            try:
                cf_proc.terminate()
                cf_proc.wait(timeout=3)
            except Exception:
                try:
                    cf_proc.kill()
                except Exception:
                    pass
            logger.info("Cloudflare tunnel yopildi.")


if __name__ == "__main__":
    main()
