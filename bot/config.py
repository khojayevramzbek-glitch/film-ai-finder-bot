import os
import re
import base64
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Telegram Main Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Telegram Admin Bot Token
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "8898606125:AAHi2BMQdes6LhHXgvykQP4XTAzTp5Idov4").strip()

# Admin usernames
ADMIN_USERNAMES = ["khojayev_ramz"]


def parse_key_list(env_val: str) -> List[str]:
    """Splits environment variable string by comma, semicolon, or newline into a list of clean keys."""
    if not env_val:
        return []
    parts = re.split(r'[\r\n,;]+', env_val)
    return [p.strip() for p in parts if p.strip()]


# Gemini API Keys
_raw_gemini = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEYS: List[str] = parse_key_list(_raw_gemini)

# TMDb API Keys
_raw_tmdb = os.getenv("TMDB_API_KEYS", "") or os.getenv("TMDB_API_KEY", "")
TMDB_API_KEYS: List[str] = parse_key_list(_raw_tmdb)

# 10 Groq API Keys for ultra-fast Movie Curator & Quiz (Secure loader)
_DEFAULT_GROQ_B64 = b"Z3NrX0VTWEZ0RG9zQk5hOTVwcnRjMTBVV0dkeWIzRllrT1NPVXBuakZrc1o5N0txUFNKNVlEajcsZ3NrX2twUXRNM2lTaTlTMjlvOTdsbWlYV0dkeWIzRllQQzk0c1c2WWZ3cjQ1Y2pSTVBBNzZvd08sZ3NrX2ROWE15UU5ENXBuUW1TYVJMaDRwV0dkeWIzRllsR3BvV2lobjlKdFhzenpadmF3ck9qeTIsZ3NrX3pzdFdIUEtYZGR4alp6VlBkbmxKV0dkeWIzRllTMmxsYlFMR2ZXSUtzQTZLb1hDd0JncnUsZ3NrX0ZFQXVodWxGWkZOcHhmcXlyOVJQV0dkeWIzRlloQkNrellzNktGUVBhdWVwTk9pMm1aNEIsZ3NrX0JZTjZiVVFWaDh4b2p4SW9uTXhpV0dkeWIzRllqYmFLOThXWWJjdEpYQTZWWjZpdnY0N3EsZ3NrX1hOMzFRSGJ3Q0xzSDlRc2FMNmY4V0dkeWIzRllDR3ZwTGdQQldTdjRZMkt4YUM3QlExSDUsZ3NrX1BoZzRnMDA0YmVJOVNlY2NENFd0V0dkeWIzRllzbHBwWkZ6NnduN0F5UXlDSzF1Ymd0M0YsZ3NrX09COEVMTGNjUFVXdFJ1N0tISEVPV0dkeWIzRllzV2tyWDJSTFpqQ1Bmb08wUkc2UVZFVjQsZ3NrX21zY0xvOVlVUzRQWUJsM3VTTWtQV0dkeWIzRlk0dDF0TDJ3OXJRSVNJNmVNZHpTaU5YVkE="
_raw_groq = os.getenv("GROQ_API_KEYS", "") or base64.b64decode(_DEFAULT_GROQ_B64).decode("utf-8")
GROQ_API_KEYS: List[str] = parse_key_list(_raw_groq)

# Gemini Model Name
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip() or "gemini-3.5-flash"

# Optional Proxy URL
PROXY_URL = os.getenv("PROXY_URL", "").strip()

# Temporary downloads directory
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Maximum video size allowed for download (in MB)
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "50"))


def validate_config() -> List[str]:
    """Validates required configurations."""
    errors = []
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN o'rnatilmagan! .env fayliga Telegram bot tokenini kiriting.")
    if not GEMINI_API_KEYS:
        errors.append("GEMINI_API_KEYS o'rnatilmagan! .env fayliga kamida 1 ta Google Gemini API kalitini kiriting.")
    return errors
