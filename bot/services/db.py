import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

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
    """Initializes database schema with users, ban status, and search logs."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 1. Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language_code TEXT NOT NULL DEFAULT 'uz',
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Add is_banned column if missing (migration)
            cursor.execute("PRAGMA table_info(users);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "is_banned" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0;")

            # 2. Searches log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    search_type TEXT NOT NULL,
                    query TEXT,
                    found INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Admins table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def is_user_banned(user_id: int) -> bool:
    """Checks if a user is banned."""
    if not user_id:
        return False
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row and row["is_banned"] == 1:
                return True
    except Exception as e:
        logger.error(f"[DB Error] is_user_banned failed: {e}")
    return False


def set_user_ban_status(user_id: int, is_banned: bool):
    """Bans or unbans a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_banned = ? WHERE user_id = ?
            """, (1 if is_banned else 0, user_id))
            conn.commit()
    except Exception as e:
        logger.error(f"[DB Error] set_user_ban_status failed: {e}")


def log_search(user_id: int, search_type: str, query: str = "", found: bool = True):
    """Logs search request for analytics."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO searches (user_id, search_type, query, found)
                VALUES (?, ?, ?, ?);
            """, (user_id, search_type, str(query)[:200], 1 if found else 0))
            conn.commit()
    except Exception as e:
        logger.warning(f"[DB Warning] log_search failed: {e}")


def get_all_active_users() -> List[int]:
    """Returns all active (non-banned) user IDs for broadcasting."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
            return [row["user_id"] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"[DB Error] get_all_active_users failed: {e}")
        return []


def get_stats() -> Dict[str, Any]:
    """Computes comprehensive statistics for Admin Dashboard."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Total users
            cursor.execute("SELECT COUNT(*) as cnt FROM users")
            total_users = cursor.fetchone()["cnt"]

            # 2. Today's users
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE date(created_at) = date('now')")
            today_users = cursor.fetchone()["cnt"]

            # 3. Banned users
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = 1")
            banned_users = cursor.fetchone()["cnt"]

            # 4. Languages distribution
            cursor.execute("SELECT language_code, COUNT(*) as cnt FROM users GROUP BY language_code")
            lang_counts = {row["language_code"]: row["cnt"] for row in cursor.fetchall()}

            # 5. Total searches
            cursor.execute("SELECT COUNT(*) as cnt FROM searches")
            total_searches = cursor.fetchone()["cnt"]

            # 6. Today's searches
            cursor.execute("SELECT COUNT(*) as cnt FROM searches WHERE date(created_at) = date('now')")
            today_searches = cursor.fetchone()["cnt"]

            # 7. Search types breakdown
            cursor.execute("SELECT search_type, COUNT(*) as cnt FROM searches GROUP BY search_type")
            search_types = {row["search_type"]: row["cnt"] for row in cursor.fetchall()}

            return {
                "total_users": total_users,
                "today_users": today_users,
                "banned_users": banned_users,
                "lang_counts": lang_counts,
                "total_searches": total_searches,
                "today_searches": today_searches,
                "search_types": search_types,
            }
    except Exception as e:
        logger.error(f"[DB Error] get_stats failed: {e}")
        return {
            "total_users": 0, "today_users": 0, "banned_users": 0,
            "lang_counts": {}, "total_searches": 0, "today_searches": 0, "search_types": {}
        }


def get_recent_users(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns the most recently active users."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, language_code, is_banned, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"[DB Error] get_recent_users failed: {e}")
        return []


# Initialize DB on module import
init_db()
