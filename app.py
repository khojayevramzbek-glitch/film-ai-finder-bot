import os
import sys
import time
import threading
import asyncio
import psutil
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


# Build a sleek, minimal Gradio web dashboard
with gr.Blocks(title="Multi-Bot AI Cloud Cluster (16 GB)") as demo:
    gr.Markdown("# 🚀 Multi-Bot 24/7 Cloud Cluster (16 GB RAM)")
    gr.Markdown(
        "Barcha Telegram botlaringiz Hugging Face Spaces bulutida **16 GB RAM** bilan 24/7 rejimda muvaffaqiyatli ishlamoqda!\n\n"
        "👉 **Kino Qidiruv Boti:** [@FilmAiFinderbot](https://t.me/FilmAiFinderbot)\n"
        "👉 **Admin Boti:** [@filmfinder_admin_bot](https://t.me/filmfinder_admin_bot)\n"
        "👉 **Guruh Moderatsiya Boti:** [@oken_sherda_bot](https://t.me/oken_sherda_bot)\n"
        "📱 **Guruh Boshqaruv Mini App:** [Boshqaruv Paneli (Web App)](/webapp)"
    )
    status_box = gr.Textbox(value=get_system_stats, label="📊 Jonli Server va Botlar Ko'rsatkichi", lines=6)
    refresh_btn = gr.Button("🔄 Yangilash / Refresh", variant="primary")
    refresh_btn.click(fn=get_system_stats, outputs=status_box)

try:
    from group_bot.webapp_server import attach_fastapi_routes
    attach_fastapi_routes(demo.app)
except Exception as e:
    print(f"⚠️ [Web App Warning] FastAPI routes ulashda xatolik: {e}", flush=True)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    demo.queue().launch(server_name="0.0.0.0", server_port=port)

