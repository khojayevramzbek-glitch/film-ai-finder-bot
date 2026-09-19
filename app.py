import os
import sys
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

import run


def run_telegram_bot():
    """Runs the main bot cluster in a background event loop."""
    print("🚀 [Hugging Face Space] Telegram Bot klasteri ishga tushirilmoqda...")
    try:
        asyncio.run(run.main())
    except Exception as e:
        print(f"❌ [Bot Fatal Error] {e}")


# Start the bot in a background daemon thread
bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
bot_thread.start()


def get_system_stats():
    """Returns live server metrics for the Gradio UI."""
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    return (
        f"🟢 Bot Holati: ONLINE (24/7)\n"
        f"🧠 RAM (Xotira): {ram.used / (1024*1024):.1f} MB / {ram.total / (1024*1024):.1f} MB ({ram.percent}%)\n"
        f"⚡️ CPU (Protsessor): {cpu}%\n"
        f"🤖 Asosiy Bot: @FilmAiFinderbot\n"
        f"👑 Admin Bot: @filmfinder_admin_bot"
    )


# Build a sleek, minimal Gradio web dashboard
with gr.Blocks(title="FilmFinder AI - 24/7 Bot Cluster") as demo:
    gr.Markdown("# 🎬 FilmFinder AI Telegram Bot Cluster")
    gr.Markdown(
        "Botingiz Hugging Face Spaces bulutida **16 GB RAM** bilan 24/7 rejimda muvaffaqiyatli ishlamoqda!\n\n"
        "👉 **Telegram Botga o'tish:** [@FilmAiFinderbot](https://t.me/FilmAiFinderbot)\n"
        "👉 **Admin Paneli:** [@filmfinder_admin_bot](https://t.me/filmfinder_admin_bot)"
    )
    status_box = gr.Textbox(value=get_system_stats, label="📊 Jonli Tizim Ko'rsatkichlari", every=5)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    demo.launch(server_name="0.0.0.0", server_port=port)
