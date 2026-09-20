import os
from pathlib import Path
from dotenv import load_dotenv

# .env fayllarini yuklash (ham group_bot ichidan, ham loyiha ildizidan)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

# GROUP_BOT_TOKEN ni o'qish (FilmFinder BOT_TOKEN bilan to'qnashmasligi uchun)
BOT_TOKEN = (
    os.getenv("GROUP_BOT_TOKEN", "").strip()
    or os.getenv("TOKEN_GROUP_BOT", "").strip()
    or os.getenv("BOT_TOKEN_GROUP", "").strip()
)

if not BOT_TOKEN:
    raise ValueError("GROUP_BOT_TOKEN topilmadi! .env fayliga yoki Space Variables ga GROUP_BOT_TOKEN ni kiriting.")
