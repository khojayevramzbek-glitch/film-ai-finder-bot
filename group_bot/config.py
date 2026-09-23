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

WEBAPP_URL_FILE = BASE_DIR / "webapp_url.txt"
DEFAULT_WEBAPP_URL = "https://uchunrisk-blizkiy-mini-app.static.hf.space"


def get_webapp_url() -> str:
    """Hozirda faol bo'lgan WebApp / Mini App URL manzilini qaytaradi."""
    if WEBAPP_URL_FILE.exists():
        try:
            saved_url = WEBAPP_URL_FILE.read_text(encoding="utf-8").strip()
            if saved_url and saved_url.startswith("http"):
                return saved_url
        except Exception:
            pass
    env_url = os.getenv("WEBAPP_URL", "").strip()
    if env_url and env_url.startswith("http"):
        return env_url
    return DEFAULT_WEBAPP_URL


def set_webapp_url(url: str):
    """Yangi WebApp URL manzilini saqlaydi va muhitga o'rnatadi."""
    url = url.strip()
    os.environ["WEBAPP_URL"] = url
    try:
        WEBAPP_URL_FILE.write_text(url, encoding="utf-8")
    except Exception:
        pass


WEBAPP_URL = get_webapp_url()
