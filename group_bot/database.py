import sqlite3
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
