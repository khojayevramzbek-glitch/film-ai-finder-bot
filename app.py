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

# ZeroGPU hook for Hugging Face Spaces
try:
    import spaces

    @spaces.GPU(duration=1)
    def dummy_gpu(x=None):
        """ZeroGPU requirement hook for Hugging Face Spaces."""
        return "ZeroGPU Ready"
except Exception:
    def dummy_gpu(x=None):
        return "CPU Ready"

# Disable internal aiohttp server in run.py so FastAPI/Gradio alone binds port 7860
os.environ["RUN_WEB_SERVER"] = "false"

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
    # ZeroGPU hook
    init_btn = gr.Button("gpu_init", visible=False)
    init_out = gr.Textbox(visible=False)
    init_btn.click(fn=dummy_gpu, inputs=[], outputs=[init_out])
    demo.load(fn=dummy_gpu, inputs=[], outputs=[init_out])


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    res = demo.queue().launch(
        server_name="0.0.0.0",
        server_port=port,
        prevent_thread_lock=True,
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
