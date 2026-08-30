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
    """Initializes database schema with users, channels, watchlist, alerts, and quiz stats."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # 1. Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    language_code TEXT NOT NULL DEFAULT 'uz',
                    is_banned INTEGER NOT NULL DEFAULT 0,
                    points INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migration: add points column if missing
            cursor.execute("PRAGMA table_info(users);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "points" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN points INTEGER NOT NULL DEFAULT 0;")
            if "is_banned" not in columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0;")

            # 2. Sponsor channels table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT UNIQUE NOT NULL,
                    channel_title TEXT NOT NULL,
                    channel_url TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Watchlist (Saved Movies)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    movie_title TEXT NOT NULL,
                    release_year TEXT,
                    poster_url TEXT,
                    rating TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, movie_title)
                );
            """)

            # 4. Premiere Alerts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS premiere_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    movie_title TEXT NOT NULL,
                    premiere_date TEXT,
                    is_notified INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, movie_title)
                );
            """)

            # 5. Searches log table
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

            conn.commit()
    except Exception as e:
        logger.error(f"[DB Init Error] Ma'lumotlar bazasini yaratishda xatolik: {e}")


# --- USER FUNCTIONS ---
def get_user_lang(user_id: int) -> Optional[str]:
    """Fetches user preferred language code."""
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
        logger.error(f"[DB Error] get_user_lang failed: {e}")
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
        logger.error(f"[DB Error] set_user_lang failed: {e}")


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
            cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if is_banned else 0, user_id))
            conn.commit()
    except Exception as e:
        logger.error(f"[DB Error] set_user_ban_status failed: {e}")


def get_user_points(user_id: int) -> int:
    """Returns user's quiz score."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row["points"] if row and row["points"] else 0
    except Exception:
        return 0


def add_user_points(user_id: int, points: int = 10):
    """Adds quiz score points to a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
            conn.commit()
    except Exception as e:
        logger.error(f"[DB Error] add_user_points failed: {e}")


def get_quiz_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns top quiz players."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, points FROM users
                WHERE points > 0
                ORDER BY points DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []


# --- SPONSOR CHANNELS ---
def get_active_channels() -> List[Dict[str, Any]]:
    """Fetches all active mandatory sponsor channels."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, channel_id, channel_title, channel_url FROM channels WHERE is_active = 1")
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"[DB Error] get_active_channels failed: {e}")
        return []


def add_sponsor_channel(channel_id: str, channel_title: str, channel_url: str):
    """Adds a new sponsor channel."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO channels (channel_id, channel_title, channel_url, is_active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(channel_id) DO UPDATE SET
                    channel_title = excluded.channel_title,
                    channel_url = excluded.channel_url,
                    is_active = 1;
            """, (channel_id.strip(), channel_title.strip(), channel_url.strip()))
            conn.commit()
    except Exception as e:
        logger.error(f"[DB Error] add_sponsor_channel failed: {e}")


def remove_sponsor_channel(channel_id: str):
    """Deactivates/removes a sponsor channel."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM channels WHERE channel_id = ? OR id = ?", (channel_id, channel_id))
            conn.commit()
    except Exception as e:
        logger.error(f"[DB Error] remove_sponsor_channel failed: {e}")


# --- WATCHLIST (SAVED MOVIES) ---
def add_to_watchlist(user_id: int, movie_title: str, release_year: str = "", poster_url: str = "", rating: str = "") -> bool:
    """Adds movie to user's saved list."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO watchlist (user_id, movie_title, release_year, poster_url, rating)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, movie_title) DO NOTHING;
            """, (user_id, movie_title.strip(), release_year, poster_url, rating))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"[DB Error] add_to_watchlist failed: {e}")
        return False


def remove_from_watchlist(user_id: int, movie_title: str) -> bool:
    """Removes movie from saved list."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE user_id = ? AND movie_title LIKE ?", (user_id, f"%{movie_title[:20]}%"))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"[DB Error] remove_from_watchlist failed: {e}")
        return False


def get_user_watchlist(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Returns user's saved movies."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT movie_title, release_year, poster_url, rating, created_at
                FROM watchlist
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"[DB Error] get_user_watchlist failed: {e}")
        return []


def is_in_watchlist(user_id: int, movie_title: str) -> bool:
    """Checks if movie is already in user's saved list."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM watchlist WHERE user_id = ? AND movie_title LIKE ?", (user_id, f"%{movie_title[:20]}%"))
            return cursor.fetchone() is not None
    except Exception:
        return False


# --- PREMIERE ALERTS ---
def add_premiere_alert(user_id: int, movie_title: str, premiere_date: str = "") -> bool:
    """Subscribes user to premiere reminder."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO premiere_alerts (user_id, movie_title, premiere_date)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, movie_title) DO NOTHING;
            """, (user_id, movie_title.strip(), premiere_date))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"[DB Error] add_premiere_alert failed: {e}")
        return False


def get_user_premiere_alerts(user_id: int) -> List[Dict[str, Any]]:
    """Returns user's active premiere reminders."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT movie_title, premiere_date, created_at
                FROM premiere_alerts
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []


# --- LOGS & STATS ---
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
    """Returns all active (non-banned) user IDs."""
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

            cursor.execute("SELECT COUNT(*) as cnt FROM users")
            total_users = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE date(created_at) = date('now')")
            today_users = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = 1")
            banned_users = cursor.fetchone()["cnt"]

            cursor.execute("SELECT language_code, COUNT(*) as cnt FROM users GROUP BY language_code")
            lang_counts = {row["language_code"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as cnt FROM searches")
            total_searches = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM searches WHERE date(created_at) = date('now')")
            today_searches = cursor.fetchone()["cnt"]

            cursor.execute("SELECT search_type, COUNT(*) as cnt FROM searches GROUP BY search_type")
            search_types = {row["search_type"]: row["cnt"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as cnt FROM watchlist")
            saved_count = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM premiere_alerts")
            alerts_count = cursor.fetchone()["cnt"]

            return {
                "total_users": total_users,
                "today_users": today_users,
                "banned_users": banned_users,
                "lang_counts": lang_counts,
                "total_searches": total_searches,
                "today_searches": today_searches,
                "search_types": search_types,
                "saved_count": saved_count,
                "alerts_count": alerts_count
            }
    except Exception as e:
        logger.error(f"[DB Error] get_stats failed: {e}")
        return {
            "total_users": 0, "today_users": 0, "banned_users": 0,
            "lang_counts": {}, "total_searches": 0, "today_searches": 0,
            "search_types": {}, "saved_count": 0, "alerts_count": 0
        }


def get_recent_users(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns the most recently active users."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, language_code, is_banned, points, created_at
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
