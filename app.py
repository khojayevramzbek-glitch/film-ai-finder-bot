import os
import sys
import time
import threading
import asyncio
import psutil
from fastapi import Request
from fastapi.responses import HTMLResponse
import gradio as gr

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Disable internal aiohttp server in run.py so FastAPI/Gradio alone binds port 7860
os.environ["RUN_WEB_SERVER"] = "false"
os.environ["GRADIO_SSR_MODE"] = "false"

import run


def run_telegram_bot():
    """Runs the main bot cluster in a background event loop."""
    print("🚀 [Hugging Face Space] Kino Bot Klasteri ishga tushirilmoqda...", flush=True)
    try:
        asyncio.run(run.main())
    except Exception as e:
        print(f"❌ [Film Bot Fatal Error] {e}", flush=True)


def run_group_bot():
    """Runs the Telegram Group Moderation Bot (@oken_sherda_bot) in a background event loop."""
    print("🛡 [Hugging Face Space] Guruh Moderatsiya Boti (@oken_sherda_bot) ishga tushirilmoqda...", flush=True)
    try:
        from group_bot import bot as group_bot_module
        asyncio.run(group_bot_module.main())
    except Exception as e:
        print(f"❌ [Group Bot Fatal Error] {e}", flush=True)


# Start both bots in background daemon threads
bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
bot_thread.start()

group_bot_thread = threading.Thread(target=run_group_bot, daemon=True)
group_bot_thread.start()


def get_system_stats():
    """Returns live server metrics for the Gradio UI."""
    try:
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        return (
            f"🟢 Server Holati: ONLINE (24/7 Doimiy)\n"
            f"🧠 RAM (Xotira): {ram.used / (1024*1024):.1f} MB / {ram.total / (1024*1024):.1f} MB ({ram.percent}%)\n"
            f"⚡️ CPU (Protsessor): {cpu}%\n"
            f"🎬 Kino Qidiruv Boti: @FilmAiFinderbot (Faol)\n"
            f"👑 Kino Admin Boti: @filmfinder_admin_bot (Faol)\n"
            f"🛡 Guruh Moderatsiya Boti: @oken_sherda_bot (Faol)"
        )
    except Exception as e:
        return f"🟢 Server Holati: ONLINE\nBotlar faol ishlamoqda. ({e})"


from starlette.middleware import Middleware
from group_bot.webapp_server import TelegramWebAppMiddleware, get_webapp_html, attach_fastapi_routes

# Build Gradio Blocks (Hugging Face Spaces ZeroGPU runner)
with gr.Blocks(
    title="Blizkiy Moderatsiya — Guruh Boshqaruv Markazi",
    css="""
        footer { display: none !important; }
        .gradio-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; background: #0b0f19 !important; }
        #component-0 { padding: 0 !important; margin: 0 !important; }
    """
) as demo:
    with gr.Column():
        gr.Markdown(
            """
            # 🛡 Blizkiy Moderatsiya & Kino AI Klasteri
            **Server Holati:** 🟢 24/7 ONLINE (Doimiy Faol)  
            **Mini App:** Telegram ilovasida to'liq integratsiya qilingan.
            """
        )
        stats_box = gr.Textbox(value=get_system_stats, every=30, label="Tizim Ko'rsatkichlari (Live)", interactive=False)


def keep_alive_worker():
    """Hugging Face CPU space 48 soatlik harakatsizlikdan uxlab qolmasligi uchun har 20 daqiqada o'zini ping qilib turadi."""
    import urllib.request
    space_host = os.getenv("SPACE_HOST") or "uchunrisk-film-ai-finder-bot.hf.space"
    target_url = f"https://{space_host}/"
    while True:
        time.sleep(1200)  # Har 20 daqiqada
        try:
            req = urllib.request.Request(target_url, headers={"User-Agent": "HF-KeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"💓 [KeepAlive] Ping yuborildi: {target_url} -> {resp.status}", flush=True)
        except Exception as e:
            print(f"⚠️ [KeepAlive] Ping ogohlantirish: {e}", flush=True)

keep_alive_thread = threading.Thread(target=keep_alive_worker, daemon=True)
keep_alive_thread.start()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    res = demo.queue().launch(
        server_name="0.0.0.0",
        server_port=port,
        prevent_thread_lock=True,
        ssr_mode=False,
        app_kwargs={
            "middleware": [Middleware(TelegramWebAppMiddleware)]
        }
    )

    # Attach routes to the active FastAPI server app as additional fallback
    if hasattr(demo, "server") and hasattr(demo.server, "app"):
        attach_fastapi_routes(demo.server.app)

    if isinstance(res, tuple):
        for item in res:
            if hasattr(item, "router"):
                attach_fastapi_routes(item)

    print(f"✅ [Server] Gradio va Mini App 0.0.0.0:{port} da muvaffaqiyatli ishga tushdi.", flush=True)

    while True:
        time.sleep(3600)
