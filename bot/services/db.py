import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "users.db"


def get_db_connection() -> sqlite3.Connection:
    """Returns thread-safe connection to SQLite with WAL mode."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn


def init_db():
    """Initializes users database and tables."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language_code TEXT NOT NULL DEFAULT 'uz',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
    except Exception as e:
        logger.error(f"[DB Init Error] Ma'lumotlar bazasini yaratishda xatolik: {e}")


def get_user_lang(user_id: int) -> Optional[str]:
    """Fetches user preferred language code from SQLite database."""
    if not user_id:
        return "uz"
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT language_code FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row["language_code"]:
                return row["language_code"]
    except Exception as e:
        logger.error(f"[DB Error] get_user_lang failed for {user_id}: {e}")
    return None


def set_user_lang(user_id: int, lang_code: str):
    """Saves or updates user preferred language code."""
    if not user_id:
        return
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, language_code, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    language_code = excluded.language_code,
                    updated_at = CURRENT_TIMESTAMP;
            """, (user_id, lang_code))
            conn.commit()
    except Exception as e:
        logger.error(f"[DB Error] set_user_lang failed for {user_id}: {e}")


# Initialize DB on module import
init_db()
