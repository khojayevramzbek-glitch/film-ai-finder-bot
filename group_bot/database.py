import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "bot_data.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Ma'lumotlar bazasi va jadvallarni ishga tushirish."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                username TEXT,
                created_at TIMESTAMP NOT NULL
            );
        """)
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN message_id INTEGER;")
        except sqlite3.OperationalError:
            pass

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_created_at
            ON messages(chat_id, created_at);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_username
            ON messages(username);
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_rules (
                chat_id INTEGER PRIMARY KEY,
                rules_text TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sleep (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                sleep_until TIMESTAMP NOT NULL,
                sleep_start TIMESTAMP NOT NULL,
                reason TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_censor_settings (
                chat_id INTEGER PRIMARY KEY,
                is_enabled INTEGER DEFAULT 1
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS custom_bad_words (
                chat_id INTEGER,
                word TEXT,
                PRIMARY KEY (chat_id, word)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_stats_settings (
                chat_id INTEGER PRIMARY KEY,
                is_enabled INTEGER DEFAULT 1,
                is_public INTEGER DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_bot_status (
                chat_id INTEGER PRIMARY KEY,
                is_enabled INTEGER DEFAULT 1
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_game_settings (
                chat_id INTEGER PRIMARY KEY,
                is_enabled INTEGER DEFAULT 1
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_authorized_users (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                is_admin INTEGER DEFAULT 1,
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prank_users (
                chat_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, username)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_virtual_mutes (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                until_ts REAL NOT NULL,
                duration_seconds INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS game_stats (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                username TEXT,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                claimed_milestones TEXT DEFAULT '',
                updated_at TIMESTAMP NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                censor_mute_seconds INTEGER DEFAULT 15,
                censor_action TEXT DEFAULT 'mute',
                flood_msg_limit INTEGER DEFAULT 5,
                flood_msg_window INTEGER DEFAULT 4,
                flood_mute_seconds INTEGER DEFAULT 900,
                flood_sticker_limit INTEGER DEFAULT 3,
                flood_sticker_window INTEGER DEFAULT 4,
                flood_sticker_mute_seconds INTEGER DEFAULT 900,
                warn_limit INTEGER DEFAULT 3,
                warn_action TEXT DEFAULT 'mute',
                warn_mute_seconds INTEGER DEFAULT 86400,
                link_filter_enabled INTEGER DEFAULT 0,
                welcome_enabled INTEGER DEFAULT 1,
                welcome_text TEXT DEFAULT 'Assalomu alaykum, {name}! Guruhimizga xush kelibsiz!',
                updated_at TIMESTAMP NOT NULL
            );
        """)

        # Ensure all columns exist in chat_settings if table was created previously
        try:
            cur = conn.execute("PRAGMA table_info(chat_settings);")
            existing_cols = {row["name"] for row in cur.fetchall()}
            needed_cols = {
                "censor_mute_seconds": "INTEGER DEFAULT 15",
                "censor_action": "TEXT DEFAULT 'mute'",
                "flood_msg_limit": "INTEGER DEFAULT 5",
                "flood_msg_window": "INTEGER DEFAULT 4",
                "flood_mute_seconds": "INTEGER DEFAULT 900",
                "flood_sticker_limit": "INTEGER DEFAULT 3",
                "flood_sticker_window": "INTEGER DEFAULT 4",
                "flood_sticker_mute_seconds": "INTEGER DEFAULT 900",
                "warn_limit": "INTEGER DEFAULT 3",
                "warn_action": "TEXT DEFAULT 'mute'",
                "warn_mute_seconds": "INTEGER DEFAULT 86400",
                "link_filter_enabled": "INTEGER DEFAULT 0",
                "welcome_enabled": "INTEGER DEFAULT 1",
                "welcome_text": "TEXT DEFAULT 'Assalomu alaykum, {name}! Guruhimizga xush kelibsiz!'",
                "updated_at": "TIMESTAMP"
            }
            for col_name, col_type in needed_cols.items():
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE chat_settings ADD COLUMN {col_name} {col_type};")
        except Exception:
            pass

        # Ensure all columns exist in chats table
        try:
            cur = conn.execute("PRAGMA table_info(chats);")
            existing_chats_cols = {row["name"] for row in cur.fetchall()}
            needed_chats_cols = {
                "username": "TEXT",
                "invite_link": "TEXT",
                "members_count": "INTEGER DEFAULT 0",
                "added_by_user_id": "INTEGER",
                "added_by_name": "TEXT",
                "added_by_username": "TEXT",
                "bot_status": "TEXT DEFAULT 'administrator'"
            }
            for col_name, col_type in needed_chats_cols.items():
                if col_name not in existing_chats_cols:
                    conn.execute(f"ALTER TABLE chats ADD COLUMN {col_name} {col_type};")
        except Exception:
            pass

        conn.commit()


def delete_message_record(chat_id: int, message_id: int):
    """O'chirilgan xabarni (so'kinish, reklama va h.k.) statadan tozalash."""
    if not message_id:
        return
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))
        conn.commit()


def add_message(chat_id: int, user_id: int, full_name: str, username: str | None = None, message_id: int | None = None):
    """Yangi kelgan xabarni bazaga yozish."""
    now_utc = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (chat_id, user_id, full_name, username, created_at, message_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, full_name, username, now_utc, message_id)
        )
        conn.commit()


def delete_flood_messages(chat_id: int, user_id: int, message_ids: list[int]):
    """Flood paytida yuborilgan xabarlarni statadan (bazadan) o'chirish."""
    with get_connection() as conn:
        if message_ids:
            placeholders = ",".join("?" for _ in message_ids)
            conn.execute(
                f"DELETE FROM messages WHERE chat_id = ? AND message_id IN ({placeholders})",
                [chat_id, *message_ids]
            )
        # Qo'shimcha xavfsizlik: o'sha foydalanuvchining so'nggi 10 soniyalik xabarlarini ham tozalash
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=10)
        conn.execute(
            "DELETE FROM messages WHERE chat_id = ? AND user_id = ? AND created_at >= ?",
            (chat_id, user_id, cutoff)
        )
        conn.commit()


def get_24h_stats(chat_id: int, limit: int = 50) -> tuple[list[dict], int, int]:
    """
    So'nggi 24 soat ichida guruhdagi faol a'zolar statistikasini olish.
    Qaytaradi: (faol a'zolar ro'yxati, jami xabarlar soni, faol a'zolar soni)
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    with get_connection() as conn:
        # Har bir a'zo bo'yicha hisob
        cursor = conn.execute(
            """
            SELECT user_id, full_name, username, COUNT(*) as msg_count
            FROM messages
            WHERE chat_id = ? AND created_at >= ?
            GROUP BY user_id
            ORDER BY msg_count DESC
            LIMIT ?
            """,
            (chat_id, cutoff_time, limit)
        )
        rows = [dict(row) for row in cursor.fetchall()]

        # Jami xabarlar va umumiy faol a'zolar soni
        summary_cur = conn.execute(
            """
            SELECT COUNT(*) as total_msgs, COUNT(DISTINCT user_id) as total_users
            FROM messages
            WHERE chat_id = ? AND created_at >= ?
            """,
            (chat_id, cutoff_time)
        )
        summary = summary_cur.fetchone()
        total_msgs = summary["total_msgs"] if summary else 0
        total_users = summary["total_users"] if summary else 0

        return rows, total_msgs, total_users


def cleanup_old_messages(days: int = 3):
    """3 kundan eski xabarlarni bazadan tozalash."""
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE created_at < ?", (cutoff_time,))
        conn.commit()


def add_warn(chat_id: int, user_id: int) -> int:
    """Foydalanuvchiga ogohlantirish qo'shish va yangi sonini qaytarish."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        new_count = (row["count"] + 1) if row else 1

        conn.execute(
            """
            INSERT INTO warnings (chat_id, user_id, count)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET count = ?
            """,
            (chat_id, user_id, new_count, new_count)
        )
        conn.commit()
        return new_count


def get_warns(chat_id: int, user_id: int) -> int:
    """Foydalanuvchining joriy ogohlantirishlar soni."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        return row["count"] if row else 0


def remove_warn(chat_id: int, user_id: int) -> int:
    """Foydalanuvchidan 1 ta ogohlantirishni olib tashlash."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        if not row or row["count"] <= 0:
            return 0
        new_count = max(0, row["count"] - 1)
        if new_count == 0:
            conn.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        else:
            conn.execute("UPDATE warnings SET count = ? WHERE chat_id = ? AND user_id = ?", (new_count, chat_id, user_id))
        conn.commit()
        return new_count


def reset_warns(chat_id: int, user_id: int):
    """Foydalanuvchi ogohlantirishlarini nollash."""
    with get_connection() as conn:
        conn.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()


def set_rules(chat_id: int, rules_text: str):
    """Guruh qoidalarini bazaga saqlash."""
    now_utc = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_rules (chat_id, rules_text, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET rules_text = ?, updated_at = ?
            """,
            (chat_id, rules_text, now_utc, rules_text, now_utc)
        )
        conn.commit()


def get_rules(chat_id: int) -> str | None:
    """Guruh qoidalarini bazadan olish."""
    with get_connection() as conn:
        cur = conn.execute("SELECT rules_text FROM chat_rules WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return row["rules_text"] if row else None


def get_user_24h_stat(chat_id: int, user_id: int) -> int:
    """Bitta foydalanuvchining so'nggi 24 soatdagi xabarlar soni."""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE chat_id = ? AND user_id = ? AND created_at >= ?",
            (chat_id, user_id, cutoff_time)
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0


def get_user_by_username(chat_id: int, username: str) -> dict | None:
    """Foydalanuvchini username bo'yicha bazadan qidirish."""
    clean_username = username.lstrip("@").strip().lower()
    with get_connection() as conn:
        # 1. Avval shu guruhning o'zidan qidirish
        cursor = conn.execute(
            """
            SELECT user_id, full_name, username 
            FROM messages 
            WHERE chat_id = ? AND LOWER(username) = ? 
            ORDER BY id DESC LIMIT 1
            """,
            (chat_id, clean_username)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # 2. Agar guruhda topilmasa, umumiy baza bo'yicha qidirish
        cursor = conn.execute(
            """
            SELECT user_id, full_name, username 
            FROM messages 
            WHERE LOWER(username) = ? 
            ORDER BY id DESC LIMIT 1
            """,
            (clean_username,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Foydalanuvchini ID bo'yicha bazadan qidirish."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT user_id, full_name, username 
            FROM messages 
            WHERE user_id = ? 
            ORDER BY id DESC LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def set_user_sleep(user_id: int, username: str | None, full_name: str, duration_seconds: int, reason: str | None = None) -> datetime:
    """Foydalanuvchi uchun uyqu / bandlik rejimini belgilash."""
    now_utc = datetime.now(timezone.utc)
    sleep_until = now_utc + timedelta(seconds=duration_seconds)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_sleep (user_id, username, full_name, sleep_until, sleep_start, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                sleep_until = excluded.sleep_until,
                sleep_start = excluded.sleep_start,
                reason = excluded.reason
            """,
            (user_id, username, full_name, sleep_until.isoformat(), now_utc.isoformat(), reason)
        )
        conn.commit()
    return sleep_until


def get_user_sleep(user_id: int) -> dict | None:
    """Foydalanuvchining faol uyqu rejimini olish. Agar muddati o'tgan bo'lsa, o'chirib None qaytaradi."""
    now_utc = datetime.now(timezone.utc)
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM user_sleep WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None

        raw_until = row["sleep_until"]
        if isinstance(raw_until, str):
            sleep_until = datetime.fromisoformat(raw_until)
        else:
            sleep_until = raw_until
        if sleep_until.tzinfo is None:
            sleep_until = sleep_until.replace(tzinfo=timezone.utc)

        if sleep_until <= now_utc:
            conn.execute("DELETE FROM user_sleep WHERE user_id = ?", (user_id,))
            conn.commit()
            return None

        raw_start = row["sleep_start"]
        if isinstance(raw_start, str):
            sleep_start = datetime.fromisoformat(raw_start)
        else:
            sleep_start = raw_start
        if sleep_start.tzinfo is None:
            sleep_start = sleep_start.replace(tzinfo=timezone.utc)

        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "full_name": row["full_name"],
            "sleep_until": sleep_until,
            "sleep_start": sleep_start,
            "reason": row["reason"]
        }


def remove_user_sleep(user_id: int):
    """Foydalanuvchini uyqu rejimidan chiqarish."""
    with get_connection() as conn:
        conn.execute("DELETE FROM user_sleep WHERE user_id = ?", (user_id,))
        conn.commit()


def get_user_sleep_by_username(username: str) -> dict | None:
    """Username bo'yicha faol uyqu rejimini olish."""
    clean = username.lstrip("@").strip().lower()
    if not clean:
        return None
    active = get_all_active_sleeps()
    for s in active:
        if s.get("username") and s["username"].lower() == clean:
            return s
    return None



def get_all_active_sleeps() -> list[dict]:
    """Barcha faol uyqudagi foydalanuvchilar ro'yxati."""
    now_utc = datetime.now(timezone.utc)
    active = []
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM user_sleep")
        rows = cur.fetchall()
        expired_ids = []
        for row in rows:
            raw_until = row["sleep_until"]
            if isinstance(raw_until, str):
                sleep_until = datetime.fromisoformat(raw_until)
            else:
                sleep_until = raw_until
            if sleep_until.tzinfo is None:
                sleep_until = sleep_until.replace(tzinfo=timezone.utc)

            if sleep_until <= now_utc:
                expired_ids.append(row["user_id"])
            else:
                raw_start = row["sleep_start"]
                if isinstance(raw_start, str):
                    sleep_start = datetime.fromisoformat(raw_start)
                else:
                    sleep_start = raw_start
                if sleep_start.tzinfo is None:
                    sleep_start = sleep_start.replace(tzinfo=timezone.utc)

                active.append({
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "full_name": row["full_name"],
                    "sleep_until": sleep_until,
                    "sleep_start": sleep_start,
                    "reason": row["reason"]
                })
        if expired_ids:
            placeholders = ",".join("?" for _ in expired_ids)
            conn.execute(f"DELETE FROM user_sleep WHERE user_id IN ({placeholders})", expired_ids)
            conn.commit()
    return active


def is_censor_enabled(chat_id: int) -> bool:
    """Guruhda censor filtri yoqilganligini tekshirish (standart: yoqilgan - True)."""
    with get_connection() as conn:
        cur = conn.execute("SELECT is_enabled FROM chat_censor_settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return bool(row["is_enabled"]) if row else True


def set_censor_status(chat_id: int, enabled: bool):
    """Guruhda censor filtrini yoqish yoki o'chirish."""
    val = 1 if enabled else 0
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_censor_settings (chat_id, is_enabled)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET is_enabled = ?
            """,
            (chat_id, val, val)
        )
        conn.commit()


def add_custom_bad_word(chat_id: int, word: str) -> bool:
    """Guruh yoki umumiy (chat_id=0) uchun yangi taqiqlangan so'z qo'shish."""
    clean_word = word.strip().strip("<>\"' ").lower()
    if not clean_word:
        return False
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO custom_bad_words (chat_id, word) VALUES (?, ?)",
            (chat_id, clean_word)
        )
        conn.commit()
    return True


def remove_custom_bad_word(chat_id: int, word: str) -> bool:
    """Guruh yoki umumiy uchun taqiqlangan so'zni ro'yxatdan chiqarish."""
    clean_word = word.strip().strip("<>\"' ").lower()
    with get_connection() as conn:
        if chat_id != 0:
            cur = conn.execute(
                "DELETE FROM custom_bad_words WHERE (chat_id = ? OR chat_id = 0) AND word = ?",
                (chat_id, clean_word)
            )
        else:
            cur = conn.execute(
                "DELETE FROM custom_bad_words WHERE word = ?",
                (clean_word,)
            )
        conn.commit()
        return cur.rowcount > 0


def get_custom_bad_words(chat_id: int = 0) -> list[str]:
    """Guruh va umumiy kiritilgan maxsus taqiqlangan so'zlar ro'yxati."""
    with get_connection() as conn:
        if chat_id != 0:
            cur = conn.execute("SELECT DISTINCT word FROM custom_bad_words WHERE chat_id IN (?, 0)", (chat_id,))
        else:
            cur = conn.execute("SELECT DISTINCT word FROM custom_bad_words WHERE chat_id = 0")
        return [row["word"] for row in cur.fetchall()]


def is_stats_enabled(chat_id: int) -> bool:
    """Guruhda statistika (stata) yoqilganligini tekshirish."""
    with get_connection() as conn:
        cur = conn.execute("SELECT is_enabled FROM chat_stats_settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return bool(row["is_enabled"]) if row else True


def set_stats_status(chat_id: int, enabled: bool):
    """Guruhda statistikani yoqish yoki o'chirish."""
    val = 1 if enabled else 0
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_stats_settings (chat_id, is_enabled)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET is_enabled = ?
            """,
            (chat_id, val, val)
        )
        conn.commit()


def is_stats_public(chat_id: int) -> bool:
    """Statistikani barcha a'zolar ko'ra oladimi yoki faqat adminlarmi."""
    with get_connection() as conn:
        cur = conn.execute("SELECT is_public FROM chat_stats_settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return bool(row["is_public"]) if row else False


def set_stats_public(chat_id: int, is_public: bool):
    """Statistikani ko'rish huquqini sozlash (barcha yoki faqat adminlar)."""
    val = 1 if is_public else 0
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_stats_settings (chat_id, is_public)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET is_public = ?
            """,
            (chat_id, val, val)
        )
        conn.commit()


def get_all_group_ids() -> list[int]:
    """Bazadagi barcha guruh chat_id larini olish."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT DISTINCT chat_id FROM messages WHERE chat_id < 0")
        return [row["chat_id"] for row in cursor.fetchall()]


def is_bot_enabled(chat_id: int) -> bool:
    """Guruhda bot umumiy holati (yoqilgan/o'chirilgan) - standart True."""
    with get_connection() as conn:
        cur = conn.execute("SELECT is_enabled FROM chat_bot_status WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if row is None:
            return True
        return bool(row["is_enabled"])


def set_bot_status(chat_id: int, enabled: bool):
    """Guruhda bot umumiy holatini yoqish yoki o'chirish."""
    val = 1 if enabled else 0
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_bot_status (chat_id, is_enabled)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET is_enabled = ?
            """,
            (chat_id, val, val)
        )
        conn.commit()


def is_game_enabled(chat_id: int) -> bool:
    """Guruhda raqam topish o'yini yoqilganligini tekshirish (standart: yoqilgan - True)."""
    with get_connection() as conn:
        cur = conn.execute("SELECT is_enabled FROM chat_game_settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if row is None:
            return True
        return bool(row["is_enabled"])


def set_game_status(chat_id: int, enabled: bool):
    """Guruhda o'yin tizimini yoqish yoki o'chirish."""
    val = 1 if enabled else 0
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_game_settings (chat_id, is_enabled)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET is_enabled = ?
            """,
            (chat_id, val, val)
        )
        conn.commit()



def get_rules(chat_id: int) -> str | None:
    """Guruh qoidalarini bazadan olish."""
    with get_connection() as conn:
        cur = conn.execute("SELECT rules_text FROM chat_rules WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return row["rules_text"] if row else None


def set_rules(chat_id: int, rules_text: str):
    """Guruh qoidalarini bazaga saqlash."""
    now_utc = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_rules (chat_id, rules_text, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET rules_text = ?, updated_at = ?
            """,
            (chat_id, rules_text, now_utc, rules_text, now_utc)
        )
        conn.commit()


BOT_OWNER_IDS = {8594505572, 7690283463}


def save_chat_title(chat_id: int, title: str):
    """Guruh nomi va chat_id sini bazaga saqlash yoki yangilash."""
    if not title:
        return
    now_utc = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chats (chat_id, title, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET title = ?, updated_at = ?
            """,
            (chat_id, title, now_utc, title, now_utc)
        )
        conn.commit()


def save_chat_full_info(
    chat_id: int,
    title: str,
    username: str | None = None,
    invite_link: str | None = None,
    members_count: int | None = None,
    added_by_user_id: int | None = None,
    added_by_name: str | None = None,
    added_by_username: str | None = None,
    bot_status: str | None = None
):
    """Guruhning to'liq ma'lumotlarini (nomi, silkasi, a'zolar soni, kim qo'shgani) bazaga saqlash."""
    if not title:
        title = f"Guruh {chat_id}"
    now_utc = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chats (chat_id, title, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET title = ?, updated_at = ?
            """,
            (chat_id, title, now_utc, title, now_utc)
        )
        
        updates = []
        params = []
        if username is not None:
            updates.append("username = ?")
            params.append(username.lstrip("@").strip() if username else None)
        if invite_link is not None:
            updates.append("invite_link = ?")
            params.append(invite_link.strip() if invite_link else None)
        if members_count is not None and members_count > 0:
            updates.append("members_count = ?")
            params.append(int(members_count))
        if added_by_user_id is not None:
            updates.append("added_by_user_id = ?")
            params.append(int(added_by_user_id))
        if added_by_name is not None:
            updates.append("added_by_name = ?")
            params.append(str(added_by_name))
        if added_by_username is not None:
            updates.append("added_by_username = ?")
            params.append(str(added_by_username).lstrip("@").strip())
        if bot_status is not None:
            updates.append("bot_status = ?")
            params.append(str(bot_status))
            
        if updates:
            sql = f"UPDATE chats SET {', '.join(updates)}, updated_at = ? WHERE chat_id = ?"
            params.extend([now_utc, chat_id])
            conn.execute(sql, params)
        conn.commit()


def record_chat_authorized_user(chat_id: int, user_id: int, is_admin: bool = True):
    """Foydalanuvchini guruh admini / ruxsat etilgan foydalanuvchisi sifatida belgilash."""
    now_utc = datetime.now(timezone.utc)
    val = 1 if is_admin else 0
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_authorized_users (chat_id, user_id, is_admin, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET is_admin = excluded.is_admin, updated_at = excluded.updated_at
            """,
            (chat_id, user_id, val, now_utc)
        )
        conn.commit()


def is_user_authorized_for_chat(chat_id: int, user_id: int | None) -> bool:
    """Foydalanuvchining ushbu guruhni boshqarishga ruxsati bormi tekshirish."""
    if not user_id:
        return False
    if user_id in BOT_OWNER_IDS:
        return True
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT 1 FROM chat_authorized_users WHERE chat_id = ? AND user_id = ? AND is_admin = 1",
            (chat_id, user_id)
        )
        if cur.fetchone():
            return True
        cur = conn.execute(
            "SELECT 1 FROM chats WHERE chat_id = ? AND added_by_user_id = ?",
            (chat_id, user_id)
        )
        return bool(cur.fetchone())


def get_user_managed_groups(user_id: int | None) -> list[dict]:
    """
    Foydalanuvchi boshqarishi mumkin bo'lgan guruhlar ro'yxati.
    - Agar bot egasi bo'lsa (@khojayev_ramz): barcha guruhlar ko'rinadi!
    - Agar oddiy admin bo'lsa: FAQAT o'zining ruxsat etilgan guruhlari ko'rinadi!
    """
    all_groups = get_all_managed_groups()
    if not user_id:
        return []
    if user_id in BOT_OWNER_IDS:
        return all_groups

    with get_connection() as conn:
        cur = conn.execute(
            "SELECT DISTINCT chat_id FROM chat_authorized_users WHERE user_id = ? AND is_admin = 1",
            (user_id,)
        )
        auth_ids = {row["chat_id"] for row in cur.fetchall()}

        cur2 = conn.execute(
            "SELECT chat_id FROM chats WHERE added_by_user_id = ?",
            (user_id,)
        )
        for row in cur2.fetchall():
            auth_ids.add(row["chat_id"])

    return [g for g in all_groups if g["chat_id"] in auth_ids]


def get_manager_overview() -> dict:
    """
    Faqat bot egasi (@khojayev_ramz) uchun:
    Barcha qo'shilgan guruhlar, ularning silkalari, a'zolari va bot holati haqida to'liq hisobot.
    """
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT 
                c.chat_id,
                COALESCE(c.title, 'Guruh ' || c.chat_id) AS title,
                c.username,
                c.invite_link,
                COALESCE(c.members_count, 0) AS members_count,
                c.added_by_user_id,
                c.added_by_name,
                c.added_by_username,
                COALESCE(c.bot_status, 'administrator') AS bot_status,
                COALESCE(b.is_enabled, 1) AS is_bot_enabled,
                COALESCE(cs.is_enabled, 1) AS is_censor_enabled,
                COALESCE(st.is_enabled, 1) AS is_stats_enabled,
                COALESCE(gm.is_enabled, 1) AS is_game_enabled,
                (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.chat_id AND m.created_at >= ?) AS msg_count_24h,
                c.updated_at
            FROM chats c
            LEFT JOIN chat_bot_status b ON c.chat_id = b.chat_id
            LEFT JOIN chat_censor_settings cs ON c.chat_id = cs.chat_id
            LEFT JOIN chat_stats_settings st ON c.chat_id = st.chat_id
            LEFT JOIN chat_game_settings gm ON c.chat_id = gm.chat_id
            WHERE c.chat_id < 0
            ORDER BY msg_count_24h DESC, c.updated_at DESC
        """, (cutoff_24h,))
        groups = [dict(r) for r in cur.fetchall()]

        # Generate default telegram link if invite_link is missing but username exists
        for g in groups:
            if not g.get("invite_link") and g.get("username"):
                g["invite_link"] = f"https://t.me/{g['username']}"

        total_groups = len(groups)
        active_groups = sum(1 for g in groups if g["is_bot_enabled"])
        total_members = sum(g["members_count"] or 0 for g in groups)
        total_msgs_24h = sum(g["msg_count_24h"] or 0 for g in groups)

        return {
            "summary": {
                "total_groups": total_groups,
                "active_groups": active_groups,
                "inactive_groups": total_groups - active_groups,
                "total_members": total_members,
                "total_msgs_24h": total_msgs_24h
            },
            "groups": groups
        }



def get_chat_title(chat_id: int) -> str:
    """Guruh nomini olish."""
    with get_connection() as conn:
        cur = conn.execute("SELECT title FROM chats WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return row["title"] if row and row["title"] else f"Guruh {chat_id}"


def get_all_managed_groups() -> list[dict]:
    """Mini App uchun barcha faol guruhlar va ularning asosiy sozlamalarini olish."""
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    with get_connection() as conn:
        cur = conn.execute("""
            SELECT 
                c.chat_id,
                COALESCE(c.title, 'Guruh ' || c.chat_id) AS title,
                COALESCE(b.is_enabled, 1) AS is_bot_enabled,
                COALESCE(cs.is_enabled, 1) AS is_censor_enabled,
                COALESCE(st.is_enabled, 1) AS is_stats_enabled,
                COALESCE(st.is_public, 0) AS is_stats_public,
                COALESCE(gm.is_enabled, 1) AS is_game_enabled,
                (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.chat_id AND m.created_at >= ?) AS msg_count_24h
            FROM chats c
            LEFT JOIN chat_bot_status b ON c.chat_id = b.chat_id
            LEFT JOIN chat_censor_settings cs ON c.chat_id = cs.chat_id
            LEFT JOIN chat_stats_settings st ON c.chat_id = st.chat_id
            LEFT JOIN chat_game_settings gm ON c.chat_id = gm.chat_id
            WHERE c.chat_id < 0
            ORDER BY msg_count_24h DESC, c.updated_at DESC
        """, (cutoff_24h,))
        rows = [dict(r) for r in cur.fetchall()]
        
        # Agar chats jadvalida bo'lmagan, lekin messages da bor guruhlar bo'lsa
        existing_ids = {r["chat_id"] for r in rows}
        cur2 = conn.execute("SELECT DISTINCT chat_id FROM messages WHERE chat_id < 0")
        for r2 in cur2.fetchall():
            cid = r2["chat_id"]
            if cid not in existing_ids:
                rows.append({
                    "chat_id": cid,
                    "title": f"Guruh {cid}",
                    "is_bot_enabled": is_bot_enabled(cid),
                    "is_censor_enabled": is_censor_enabled(cid),
                    "is_stats_enabled": is_stats_enabled(cid),
                    "is_stats_public": is_stats_public(cid),
                    "is_game_enabled": is_game_enabled(cid),
                    "msg_count_24h": 0
                })
        return rows


DEFAULT_WELCOME_TEXT = (
    "✨ <b>Xush kelibsiz, {mention}!</b>\n\n"
    "Hurmatli ishtirokchi, <b>«{title}»</b> jamoasiga qo‘shilganingizdan mamnunmiz!\n\n"
    "<blockquote>🤝 <b>Guruh tartib-qoidalari:</b>\n"
    "• O‘zaro hurmat va madaniyatli muloqot;\n"
    "• Reklama, haqorat va keraksiz spamlardan tiyilish;\n"
    "• Mavzuga doir mazmunli va foydali suhbatlar.</blockquote>\n\n"
    "<i>Sizga guruhimizda maroqli va samarali vaqt tilaymiz!</i>"
)

DEFAULT_CHAT_SETTINGS = {
    "censor_mute_seconds": 15,
    "censor_action": "mute",
    "flood_msg_limit": 5,
    "flood_msg_window": 4,
    "flood_mute_seconds": 900,
    "flood_sticker_limit": 3,
    "flood_sticker_window": 4,
    "flood_sticker_mute_seconds": 900,
    "warn_limit": 10,
    "warn_action": "smart",
    "warn_mute_seconds": 3600,
    "link_filter_enabled": 0,
    "welcome_enabled": 1,
    "welcome_text": DEFAULT_WELCOME_TEXT
}


def format_duration(seconds: int) -> str:
    """Vaqtni soniyalardan inson tushunadigan o'zbekcha matnga aylantirish (sekunddan yilgacha)."""
    sec = int(seconds)
    if sec < 60:
        return f"{sec} soniya"
    elif sec < 3600:
        mins = sec // 60
        return f"{mins} daqiqa"
    elif sec < 86400:
        hrs = sec // 3600
        return f"{hrs} soat"
    elif sec < 604800:
        days = sec // 86400
        return f"{days} kun"
    elif sec < 2592000:
        weeks = sec // 604800
        return f"{weeks} hafta"
    elif sec < 31536000:
        months = sec // 2592000
        return f"{months} oy"
    else:
        years = sec // 31536000
        return f"{years} yil"


def get_chat_full_settings(chat_id: int) -> dict:
    """Guruhning barcha sozlamalarini (mute/ban daqiqalari, flood, warn va h.k.) olish."""
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if not row:
            res = dict(DEFAULT_CHAT_SETTINGS)
            res["chat_id"] = chat_id
            return res
        res = dict(row)
        if not res.get("welcome_text") or res.get("welcome_text") == "Assalomu alaykum, {name}! Guruhimizga xush kelibsiz!":
            res["welcome_text"] = DEFAULT_WELCOME_TEXT
        return res


def update_chat_settings(chat_id: int, settings: dict):
    """Guruh sozlamalarini yangilash."""
    now_utc = datetime.now(timezone.utc)
    current = get_chat_full_settings(chat_id)
    current.update(settings)
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO chat_settings (
                chat_id, censor_mute_seconds, censor_action,
                flood_msg_limit, flood_msg_window, flood_mute_seconds,
                flood_sticker_limit, flood_sticker_window, flood_sticker_mute_seconds,
                warn_limit, warn_action, warn_mute_seconds,
                link_filter_enabled, welcome_enabled, welcome_text, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                censor_mute_seconds = excluded.censor_mute_seconds,
                censor_action = excluded.censor_action,
                flood_msg_limit = excluded.flood_msg_limit,
                flood_msg_window = excluded.flood_msg_window,
                flood_mute_seconds = excluded.flood_mute_seconds,
                flood_sticker_limit = excluded.flood_sticker_limit,
                flood_sticker_window = excluded.flood_sticker_window,
                flood_sticker_mute_seconds = excluded.flood_sticker_mute_seconds,
                warn_limit = excluded.warn_limit,
                warn_action = excluded.warn_action,
                warn_mute_seconds = excluded.warn_mute_seconds,
                link_filter_enabled = excluded.link_filter_enabled,
                welcome_enabled = excluded.welcome_enabled,
                welcome_text = excluded.welcome_text,
                updated_at = excluded.updated_at
        """, (
            chat_id,
            int(current.get("censor_mute_seconds", 15)),
            str(current.get("censor_action", "mute")),
            int(current.get("flood_msg_limit", 5)),
            int(current.get("flood_msg_window", 4)),
            int(current.get("flood_mute_seconds", 900)),
            int(current.get("flood_sticker_limit", 3)),
            int(current.get("flood_sticker_window", 4)),
            int(current.get("flood_sticker_mute_seconds", 900)),
            int(current.get("warn_limit", 3)),
            str(current.get("warn_action", "mute")),
            int(current.get("warn_mute_seconds", 86400)),
            int(current.get("link_filter_enabled", 0)),
            int(current.get("welcome_enabled", 1)),
            str(current.get("welcome_text", "Assalomu alaykum, {name}! Guruhimizga xush kelibsiz!")),
            now_utc
        ))
        conn.commit()


def get_group_details(chat_id: int) -> dict:
    """Tanlangan guruhning to'liq sozlamalari, taqiqlangan so'zlari, qoidalari va statistikasini olish."""
    title = get_chat_title(chat_id)
    bot_enabled = is_bot_enabled(chat_id)
    censor_enabled = is_censor_enabled(chat_id)
    stats_enabled = is_stats_enabled(chat_id)
    stats_public = is_stats_public(chat_id)
    game_enabled = is_game_enabled(chat_id)
    bad_words = get_custom_bad_words(chat_id)
    rules = get_rules(chat_id) or ""
    settings = get_chat_full_settings(chat_id)
    
    top_users, total_msgs, active_users = get_24h_stats(chat_id, limit=20)
    prank_users = get_prank_users(chat_id)
    
    return {
        "chat_id": chat_id,
        "title": title,
        "is_bot_enabled": bot_enabled,
        "is_censor_enabled": censor_enabled,
        "is_stats_enabled": stats_enabled,
        "is_stats_public": stats_public,
        "is_game_enabled": game_enabled,
        "bad_words": bad_words,
        "rules": rules,
        "settings": settings,
        "prank_users": prank_users,
        "stats": {
            "total_messages": total_msgs,
            "active_users": active_users,
            "top_users": top_users
        }
    }


def add_prank_user(chat_id: int, username: str) -> tuple[bool, str]:
    """Hazil rejimi (Ghost mode) uchun username qo'shish (ko'pi bilan 5 ta)."""
    clean_username = username.lstrip("@").strip().lower()
    if not clean_username:
        return False, "Username kiritilmadi!"
    if clean_username in {"khojayev_ramz", "wdablyu"}:
        return False, "Bot egasini Hazil rejimiga qo'shib bo'lmaydi!"
    
    with get_connection() as conn:
        cur = conn.execute("SELECT count(*) as cnt FROM prank_users WHERE chat_id = ?", (chat_id,))
        count = cur.fetchone()["cnt"]
        if count >= 5:
            return False, "Maksimal 5 ta foydalanuvchi kiritish mumkin!"
        
        cur = conn.execute("SELECT 1 FROM prank_users WHERE chat_id = ? AND username = ?", (chat_id, clean_username))
        if cur.fetchone():
            return False, f"@{clean_username} allaqachon ro'yxatda bor!"
            
        conn.execute(
            "INSERT INTO prank_users (chat_id, username) VALUES (?, ?)",
            (chat_id, clean_username)
        )
        conn.commit()
        return True, f"@{clean_username} Hazil rejimiga qo'shildi!"


def remove_prank_user(chat_id: int, username: str) -> bool:
    """Hazil rejimidan usernameni o'chirish."""
    clean_username = username.lstrip("@").strip().lower()
    with get_connection() as conn:
        conn.execute("DELETE FROM prank_users WHERE chat_id = ? AND username = ?", (chat_id, clean_username))
        conn.commit()
        return True


def get_prank_users(chat_id: int) -> list[str]:
    """Guruhdagi barcha hazil rejimidagi username'larni olish."""
    with get_connection() as conn:
        cur = conn.execute("SELECT username FROM prank_users WHERE chat_id = ? ORDER BY created_at ASC", (chat_id,))
        return [row["username"] for row in cur.fetchall()]


def is_prank_user(chat_id: int, username: str | None) -> bool:
    """Foydalanuvchi hazil rejimidami tekshirish."""
    if not username:
        return False
    clean_username = username.lstrip("@").strip().lower()
    if clean_username in {"khojayev_ramz", "wdablyu"}:
        return False
    with get_connection() as conn:
        cur = conn.execute("SELECT 1 FROM prank_users WHERE chat_id = ? AND username = ?", (chat_id, clean_username))
        return cur.fetchone() is not None


# -------------------------------------------------------------
# Adminlar uchun «Virtual Mute» Kesh va Baza funksiyalari
# -------------------------------------------------------------
_admin_virtual_mutes_cache: dict[tuple[int, int], float] = {}


def init_admin_virtual_mutes_cache():
    """Bot ishga tushganda faol virtual mutelarni xotiraga (RAM) yuklash."""
    now = time.time()
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT chat_id, user_id, until_ts FROM admin_virtual_mutes WHERE until_ts > ?", (now,))
            _admin_virtual_mutes_cache.clear()
            for row in cur.fetchall():
                _admin_virtual_mutes_cache[(int(row["chat_id"]), int(row["user_id"]))] = float(row["until_ts"])
    except Exception:
        _admin_virtual_mutes_cache.clear()


def set_admin_virtual_mute(chat_id: int, user_id: int, duration_seconds: int) -> float:
    """Adminni virtual mute qilish va bazaga hamda xotiraga saqlash."""
    until_ts = time.time() + duration_seconds
    _admin_virtual_mutes_cache[(chat_id, user_id)] = until_ts
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO admin_virtual_mutes (chat_id, user_id, until_ts, duration_seconds)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                until_ts = excluded.until_ts,
                duration_seconds = excluded.duration_seconds,
                created_at = CURRENT_TIMESTAMP
        """, (chat_id, user_id, until_ts, duration_seconds))
        conn.commit()
    return until_ts


def remove_admin_virtual_mute(chat_id: int, user_id: int) -> bool:
    """Adminni virtual mutedan chiqarish."""
    _admin_virtual_mutes_cache.pop((chat_id, user_id), None)
    with get_connection() as conn:
        conn.execute("DELETE FROM admin_virtual_mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()
    return True


def is_admin_virtually_muted(chat_id: int, user_id: int) -> bool:
    """Admin ayni damda virtual mutedami (O(1) mikrosoniya tekshiruv)."""
    now = time.time()
    until_ts = _admin_virtual_mutes_cache.get((chat_id, user_id))
    if until_ts is not None:
        if now < until_ts:
            return True
        else:
            # Vaqti tugagan, kesh va bazadan tozalash
            _admin_virtual_mutes_cache.pop((chat_id, user_id), None)
            try:
                with get_connection() as conn:
                    conn.execute("DELETE FROM admin_virtual_mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
                    conn.commit()
            except Exception:
                pass
            return False
    return False


def get_admin_virtual_mute_remaining(chat_id: int, user_id: int) -> int | None:
    """Adminning qolgan mute soniyalarini olish."""
    now = time.time()
    until_ts = _admin_virtual_mutes_cache.get((chat_id, user_id))
    if until_ts and until_ts > now:
        return int(until_ts - now)
    return None


# -------------------------------------------------------------
# «Raqamni Top» O'yin Statistikasi va Sovg'alar Baza Funksiyalari
# -------------------------------------------------------------

def record_game_result(
    chat_id: int,
    winner_id: int,
    winner_name: str,
    winner_uname: str | None,
    loser_id: int,
    loser_name: str,
    loser_uname: str | None
) -> tuple[int, list[int]]:
    """
    O'yin natijasini bazaga yozish:
    G'olibga +1 g'alaba, mag'lubga +1 mag'lubiyat.
    Agar g'olib yangi marraga (30, 50, 100) yetgan bo'lsa, uni qaytaradi.
    Qaytaradi: (winner_wins, new_milestones_list)
    """
    now = datetime.now(timezone.utc).isoformat()
    new_milestones = []

    with get_connection() as conn:
        # 1. G'olibning joriy statistikasini olish
        cur = conn.execute("SELECT wins, claimed_milestones FROM game_stats WHERE chat_id = ? AND user_id = ?", (chat_id, winner_id))
        row = cur.fetchone()
        if row:
            curr_wins = row["wins"] + 1
            claimed = set(row["claimed_milestones"].split(",")) if row["claimed_milestones"] else set()
        else:
            curr_wins = 1
            claimed = set()

        # Marraga erishilganmi (30, 50, 100)?
        for m in (30, 50, 100):
            if curr_wins >= m and str(m) not in claimed:
                new_milestones.append(m)
                claimed.add(str(m))

        claimed_str = ",".join(sorted(claimed, key=lambda x: int(x) if x.isdigit() else 0))

        # G'olibni yangilash
        conn.execute("""
            INSERT INTO game_stats (chat_id, user_id, full_name, username, wins, losses, total_games, claimed_milestones, updated_at)
            VALUES (?, ?, ?, ?, 1, 0, 1, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                wins = wins + 1,
                total_games = total_games + 1,
                claimed_milestones = excluded.claimed_milestones,
                updated_at = excluded.updated_at
        """, (chat_id, winner_id, winner_name, winner_uname, claimed_str, now))

        # Mag'lubni yangilash
        conn.execute("""
            INSERT INTO game_stats (chat_id, user_id, full_name, username, wins, losses, total_games, claimed_milestones, updated_at)
            VALUES (?, ?, ?, ?, 0, 1, 1, '', ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                losses = losses + 1,
                total_games = total_games + 1,
                updated_at = excluded.updated_at
        """, (chat_id, loser_id, loser_name, loser_uname, now))

        conn.commit()
        return curr_wins, new_milestones


def get_user_game_stats(chat_id: int, user_id: int) -> dict | None:
    """Foydalanuvchining o'yin statistikasini olish."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT full_name, username, wins, losses, total_games, claimed_milestones FROM game_stats WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        row = cur.fetchone()
        if row:
            return dict(row)
        return None


def get_top_game_players(chat_id: int, limit: int = 10) -> list[dict]:
    """Guruhdagi eng ko'p g'alaba qozongan o'yinchilar TOP reytingi."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT user_id, full_name, username, wins, losses, total_games, claimed_milestones FROM game_stats WHERE chat_id = ? AND wins > 0 ORDER BY wins DESC LIMIT ?",
            (chat_id, limit)
        )
        return [dict(row) for row in cur.fetchall()]



