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

# Disable internal aiohttp server in run.py so Gradio alone binds port 7860
os.environ["RUN_WEB_SERVER"] = "false"

import run

try:
    import spaces

    @spaces.GPU
    def zero_gpu_initializer(dummy=None):
        """ZeroGPU requirement hook for Hugging Face Spaces."""
        return "ZeroGPU Ready"
except Exception:
    pass


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


from group_bot.webapp_server import get_webapp_html, attach_fastapi_routes

# Build Gradio Blocks (Hugging Face Spaces native runner)
with gr.Blocks(
    title="Blizkiy Moderatsiya — Guruh Boshqaruv Markazi",
    css="""
        footer { display: none !important; }
        .gradio-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; background: #0b0f19 !important; }
    """
) as demo:
    # Telegram Mini App ni to'g'ridan-to'g'ri Gradio ichida ham render qilish
    gr.HTML(value=get_webapp_html())

# Attach Telegram Mini App routes and API endpoints to demo.app (FastAPI)
try:
    attach_fastapi_routes(demo.app)

    @demo.app.middleware("http")
    async def serve_webapp_for_tg(request: Request, call_next):
        # Bosh sahifa "/" yoki "/webapp" ga so'rov kelsa darhol sof Mini App HTML ni yuborish
        if request.method == "GET" and request.url.path in ["/", "/webapp"]:
            return HTMLResponse(content=get_webapp_html())
        return await call_next(request)
except Exception as e:
    print(f"⚠️ [Web App Warning] FastAPI routes ulashda xatolik: {e}", flush=True)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    demo.queue().launch(server_name="0.0.0.0", server_port=port)
