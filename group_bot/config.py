import os
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# GROUP_BOT_TOKEN ni o'qish (FilmFinder BOT_TOKEN bilan to'qnashmasligi uchun)
BOT_TOKEN = os.getenv("GROUP_BOT_TOKEN") or os.getenv("TOKEN_GROUP_BOT") or "8953289535:AAEgCw-TNlydyzigch-_1A2nzRA9qUV9bSw"

if not BOT_TOKEN:
    raise ValueError("GROUP_BOT_TOKEN topilmadi!")

