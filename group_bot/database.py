import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "bot_data.db"
UZB_TZ = timezone(timedelta(hours=5))


def get_uzb_now() -> datetime:
    """O'zbekiston vaqti (Toshkent, UTC+5)."""
    return datetime.now(UZB_TZ)


def get_uzb_now_str() -> str:
    """O'zbekiston vaqti ISO satri: 'YYYY-MM-DD HH:MM:SS+05:00'."""
    return get_uzb_now().strftime("%Y-%m-%d %H:%M:%S+05:00")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
    except Exception:
        pass
    return conn


def init_db():
    """Ma'lumotlar bazasi va jadvallarni ishga tushirish."""
    with get_connection() as conn:
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass

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
            CREATE INDEX IF NOT EXISTS idx_messages_chat_user_created
            ON messages(chat_id, user_id, created_at);
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
            CREATE TABLE IF NOT EXISTS user_sleep_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sleep_logs_user_time
            ON user_sleep_logs(user_id, created_at);
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
                user_id INTEGER DEFAULT 0,
                mode TEXT DEFAULT 'emoji',
                full_name TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, username)
            );
        """)
        try:
            conn.execute("ALTER TABLE prank_users ADD COLUMN user_id INTEGER DEFAULT 0;")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE prank_users ADD COLUMN mode TEXT DEFAULT 'emoji';")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE prank_users ADD COLUMN full_name TEXT DEFAULT '';")
        except Exception:
            pass
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prank_users_chat_uid
            ON prank_users(chat_id, user_id);
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
            CREATE TABLE IF NOT EXISTS group_members (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                username TEXT,
                joined_at TIMESTAMP NOT NULL,
                first_seen TIMESTAMP NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                is_exact_join INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            );
        """)
        try:
            conn.execute("ALTER TABLE group_members ADD COLUMN is_exact_join INTEGER DEFAULT 0;")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE group_members ADD COLUMN total_messages INTEGER DEFAULT 0;")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                reason TEXT DEFAULT '',
                duration_seconds INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_punishments_chat_user
            ON user_punishments(chat_id, user_id);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_punishments_chat_user_act_created
            ON user_punishments(chat_id, user_id, action_type, created_at);
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
            CREATE TABLE IF NOT EXISTS known_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                last_chat_id INTEGER,
                updated_at TIMESTAMP NOT NULL
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_known_users_username
            ON known_users(username COLLATE NOCASE);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_known_users_chat
            ON known_users(last_chat_id);
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS authorized_taggers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_authorized_taggers_uname
            ON authorized_taggers(username COLLATE NOCASE);
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
                "anti_channel_enabled": "INTEGER DEFAULT 1",
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

        # Seed primary group and owner authorization if starting on new server
        try:
            now_utc = datetime.now(timezone.utc)
            conn.execute("""
                INSERT INTO chats (chat_id, title, invite_link, added_by_user_id, added_by_name, added_by_username, bot_status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title = COALESCE(chats.title, excluded.title),
                    invite_link = COALESCE(chats.invite_link, excluded.invite_link),
                    updated_at = excluded.updated_at
            """, (
                -1003834509976,
                "Близкий🫶",
                "https://t.me/+PM3yYk0OwA04MDJi",
                8594505572,
                "Ramzbek",
                "khojayev_ramz",
                "administrator",
                now_utc
            ))
            conn.execute("""
                INSERT INTO chat_authorized_users (chat_id, user_id, is_admin, updated_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET is_admin = 1, updated_at = excluded.updated_at
            """, (
                -1003834509976,
                8594505572,
                now_utc
            ))

            # Guruh o'yini: Ramzbek (@khojayev_ramz - 3 g'alaba) va Shoodilv (@shoodilv - 1 g'alaba) ni boshlang'ich tiklash
            conn.execute("""
                INSERT INTO game_stats (chat_id, user_id, full_name, username, wins, losses, total_games, claimed_milestones, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, '', ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    wins = MAX(game_stats.wins, excluded.wins),
                    total_games = MAX(game_stats.total_games, excluded.total_games),
                    username = COALESCE(excluded.username, game_stats.username),
                    full_name = COALESCE(excluded.full_name, game_stats.full_name),
                    updated_at = excluded.updated_at
            """, (
                -1003834509976,
                8594505572,
                "рамз",
                "khojayev_ramz",
                3,
                1,
                4,
                now_utc.isoformat()
            ))

            conn.execute("""
                INSERT INTO game_stats (chat_id, user_id, full_name, username, wins, losses, total_games, claimed_milestones, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, '', ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    wins = MAX(game_stats.wins, excluded.wins),
                    total_games = MAX(game_stats.total_games, excluded.total_games),
                    username = COALESCE(excluded.username, game_stats.username),
                    full_name = COALESCE(excluded.full_name, game_stats.full_name),
                    updated_at = excluded.updated_at
            """, (
                -1003834509976,
                8573235489,
                "Шоодилов",
                "shoodilv",
                1,
                3,
                4,
                now_utc.isoformat()
            ))
            # 4. known_users katalogini messages va game_stats dan to'ldirish (Backfill)
            conn.execute("""
                INSERT OR IGNORE INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
                SELECT user_id, username, full_name, chat_id, created_at
                FROM (
                    SELECT user_id, username, full_name, chat_id, created_at
                    FROM messages
                    WHERE user_id IS NOT NULL AND user_id > 0
                    ORDER BY id DESC
                )
                GROUP BY user_id;
            """)
            conn.execute("""
                INSERT OR IGNORE INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
                SELECT user_id, username, full_name, chat_id, updated_at
                FROM game_stats
                WHERE user_id IS NOT NULL AND user_id > 0;
            """)
            conn.execute("""
                INSERT INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
                VALUES (8594505572, 'khojayev_ramz', 'Ramzbek', -1003834509976, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    updated_at = excluded.updated_at;
            """, (now_utc.isoformat(),))
            conn.execute("""
                INSERT INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
                VALUES (7690283463, 'wdablyu', 'Wdablyu', -1003834509976, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    updated_at = excluded.updated_at;
            """, (now_utc.isoformat(),))
        except Exception:
            pass

        conn.commit()
    try:
        init_prank_users_cache()
    except Exception:
        pass


def upsert_known_user(user_id: int, full_name: str, username: str | None = None, chat_id: int | None = None):
    """
    Foydalanuvchini doimiy foydalanuvchilar katalogiga (known_users) yozish yoki yangilash.
    Ushbu jadval 3 kundan keyin tozalanmaydi, butunlay saqlanib qoladi.
    """
    if not user_id or user_id <= 0:
        return
    clean_username = username.lstrip("@").strip() if username else None
    clean_full_name = (full_name or "").strip() or f"Foydalanuvchi [{user_id}]"
    now_utc = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(excluded.username, known_users.username),
                    full_name = CASE WHEN excluded.full_name != '' THEN excluded.full_name ELSE known_users.full_name END,
                    last_chat_id = COALESCE(excluded.last_chat_id, known_users.last_chat_id),
                    updated_at = excluded.updated_at
                """,
                (user_id, clean_username, clean_full_name, chat_id, now_utc)
            )
            conn.commit()
    except Exception:
        pass


def delete_message_record(chat_id: int, message_id: int):
    """O'chirilgan xabarni (so'kinish, reklama va h.k.) statadan tozalash."""
    if not message_id:
        return
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ? AND message_id = ?", (chat_id, message_id))
        conn.commit()


def add_message(chat_id: int, user_id: int, full_name: str, username: str | None = None, message_id: int | None = None):
    """Yangi kelgan xabarni bazaga yozish va doimiy katalogga muhrlash (yagona tranzaksiya)."""
    now_uzb = get_uzb_now()
    now_uzb_str = now_uzb.strftime("%Y-%m-%d %H:%M:%S+05:00")
    now_iso = now_uzb.isoformat()
    clean_username = username.lstrip("@").strip() if username else None
    clean_full_name = (full_name or "").strip() or f"Foydalanuvchi [{user_id}]"

    with get_connection() as conn:
        # 1. messages jadvaliga yozish
        conn.execute(
            """
            INSERT INTO messages (chat_id, user_id, full_name, username, created_at, message_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, full_name, username, now_uzb_str, message_id)
        )
        # 2. known_users katalogiga yozish
        if user_id and user_id > 0:
            conn.execute(
                """
                INSERT INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(excluded.username, known_users.username),
                    full_name = CASE WHEN excluded.full_name != '' THEN excluded.full_name ELSE known_users.full_name END,
                    last_chat_id = COALESCE(excluded.last_chat_id, known_users.last_chat_id),
                    updated_at = excluded.updated_at
                """,
                (user_id, clean_username, clean_full_name, chat_id, now_iso)
            )
        # 3. group_members jadvalini yangilash
        conn.execute(
            """
            INSERT INTO group_members (chat_id, user_id, full_name, username, joined_at, first_seen, last_seen, is_exact_join, total_messages)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = COALESCE(excluded.username, group_members.username),
                last_seen = excluded.last_seen,
                total_messages = COALESCE(group_members.total_messages, 0) + 1
            """,
            (chat_id, user_id, full_name, username, now_uzb_str, now_uzb_str, now_uzb_str)
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
        cutoff_ts = int(time.time()) - 10
        conn.execute(
            "DELETE FROM messages WHERE chat_id = ? AND user_id = ? AND (unixepoch(created_at) >= ? OR datetime(created_at) >= datetime(?, 'unixepoch'))",
            (chat_id, user_id, cutoff_ts, cutoff_ts)
        )
        conn.commit()


def get_24h_stats(chat_id: int, limit: int = 50) -> tuple[list[dict], int, int]:
    """
    So'nggi 24 soat ichida guruhdagi faol a'zolar statistikasini olish (O'zbekiston vaqti).
    Qaytaradi: (faol a'zolar ro'yxati, jami xabarlar soni, faol a'zolar soni)
    """
    cutoff_24h_ts = int(time.time()) - (24 * 3600)
    with get_connection() as conn:
        # Har bir a'zo bo'yicha hisob
        cursor = conn.execute(
            """
            SELECT user_id, full_name, username, COUNT(*) as msg_count
            FROM messages
            WHERE chat_id = ? AND (unixepoch(created_at) >= ? OR datetime(created_at) >= datetime(?, 'unixepoch'))
            GROUP BY user_id
            ORDER BY msg_count DESC
            LIMIT ?
            """,
            (chat_id, cutoff_24h_ts, cutoff_24h_ts, limit)
        )
        rows = [dict(row) for row in cursor.fetchall()]

        # Jami xabarlar va umumiy faol a'zolar soni
        summary_cur = conn.execute(
            """
            SELECT COUNT(*) as total_msgs, COUNT(DISTINCT user_id) as total_users
            FROM messages
            WHERE chat_id = ? AND (unixepoch(created_at) >= ? OR datetime(created_at) >= datetime(?, 'unixepoch'))
            """,
            (chat_id, cutoff_24h_ts, cutoff_24h_ts)
        )
        summary = summary_cur.fetchone()
        total_msgs = summary["total_msgs"] if summary else 0
        total_users = summary["total_users"] if summary else 0

        return rows, total_msgs, total_users


def cleanup_old_messages(days: int = 3):
    """3 kundan eski xabarlarni bazadan tozalash."""
    cutoff_ts = int(time.time()) - (days * 86400)
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE (unixepoch(created_at) < ? OR datetime(created_at) < datetime(?, 'unixepoch'))", (cutoff_ts, cutoff_ts))
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
    """Bitta foydalanuvchining so'nggi 24 soatdagi xabarlar soni (O'zbekiston vaqti)."""
    cutoff_24h_ts = int(time.time()) - (24 * 3600)
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) as cnt 
            FROM messages 
            WHERE chat_id = ? AND user_id = ? 
              AND (unixepoch(created_at) >= ? OR datetime(created_at) >= datetime(?, 'unixepoch'))
            """,
            (chat_id, user_id, cutoff_24h_ts, cutoff_24h_ts)
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0


def get_user_by_username(chat_id: int, username: str) -> dict | None:
    """
    Foydalanuvchini username bo'yicha super-tergov qidiruvi (Waterfall Lookup):
    1. known_users - aynan shu guruhda ko'rilgan
    2. known_users - barcha guruhlar bo'yicha global qidiruv
    3. messages - shu guruhdagi so'nggi xabarlar
    4. messages - umumiy xabarlar bazasi
    5. game_stats - o'yin o'ynaganlar bazasi
    """
    clean_username = username.lstrip("@").strip().lower()
    if not clean_username:
        return None

    with get_connection() as conn:
        # 1. known_users (shu guruh)
        if chat_id:
            cur = conn.execute(
                """
                SELECT user_id, full_name, username 
                FROM known_users 
                WHERE last_chat_id = ? AND LOWER(username) = ? 
                LIMIT 1
                """,
                (chat_id, clean_username)
            )
            row = cur.fetchone()
            if row:
                return dict(row)

        # 2. known_users (umumiy)
        cur = conn.execute(
            """
            SELECT user_id, full_name, username 
            FROM known_users 
            WHERE LOWER(username) = ? 
            ORDER BY updated_at DESC LIMIT 1
            """,
            (clean_username,)
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        # 3. messages (shu guruh)
        if chat_id:
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
                upsert_known_user(row["user_id"], row["full_name"], row["username"], chat_id)
                return dict(row)

        # 4. messages (umumiy)
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
        if row:
            upsert_known_user(row["user_id"], row["full_name"], row["username"], chat_id)
            return dict(row)

        # 5. game_stats
        cursor = conn.execute(
            """
            SELECT user_id, full_name, username 
            FROM game_stats 
            WHERE LOWER(username) = ? 
            ORDER BY updated_at DESC LIMIT 1
            """,
            (clean_username,)
        )
        row = cursor.fetchone()
        if row:
            upsert_known_user(row["user_id"], row["full_name"], row["username"], chat_id)
            return dict(row)

    return None


def get_user_by_id(user_id: int) -> dict | None:
    """Foydalanuvchini ID bo'yicha super-tergov qidiruvi."""
    if not user_id:
        return None
    with get_connection() as conn:
        # 1. known_users
        cur = conn.execute(
            "SELECT user_id, full_name, username FROM known_users WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        # 2. messages
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
        if row:
            upsert_known_user(row["user_id"], row["full_name"], row["username"])
            return dict(row)

        # 3. game_stats
        cursor = conn.execute(
            """
            SELECT user_id, full_name, username 
            FROM game_stats 
            WHERE user_id = ? 
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            upsert_known_user(row["user_id"], row["full_name"], row["username"])
            return dict(row)

    return None


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


def get_user_sleep_count_24h(user_id: int) -> int:
    """Foydalanuvchi so'nggi 24 soat ichida necha marta sleep rejimiga o'tganini hisoblash."""
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT count(*) as cnt FROM user_sleep_logs WHERE user_id = ? AND created_at >= ?",
            (user_id, cutoff_24h.isoformat())
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0


def log_user_sleep_usage(user_id: int, chat_id: int | None = None):
    """Foydalanuvchi uyqu rejimini ishlatganini log qilish (24 soatlik limit tekshiruvi uchun)."""
    now_utc = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO user_sleep_logs (user_id, chat_id, created_at) VALUES (?, ?, ?)",
            (user_id, chat_id, now_utc.isoformat())
        )
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


# -------------------------------------------------------------
# Tezkor RAM keshlar (Disk I/O va SQLite qulfini 0 ga tushirish)
# -------------------------------------------------------------
_bot_status_cache: dict[int, bool] = {}
_censor_status_cache: dict[int, bool] = {}
_chat_settings_cache: dict[int, dict] = {}
_bad_words_cache: dict[int, list[str]] = {}


def is_censor_enabled(chat_id: int) -> bool:
    """Guruhda censor filtri yoqilganligini tekshirish (RAM kesh: 0.0001ms)."""
    if chat_id in _censor_status_cache:
        return _censor_status_cache[chat_id]
    with get_connection() as conn:
        cur = conn.execute("SELECT is_enabled FROM chat_censor_settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        val = bool(row["is_enabled"]) if row else True
        _censor_status_cache[chat_id] = val
        return val


def set_censor_status(chat_id: int, enabled: bool):
    """Guruhda censor filtrini yoqish yoki o'chirish."""
    _censor_status_cache[chat_id] = enabled
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
    _bad_words_cache.clear()
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
    _bad_words_cache.clear()
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
    """Guruh va umumiy kiritilgan maxsus taqiqlangan so'zlar ro'yxati (RAM kesh)."""
    if chat_id in _bad_words_cache:
        return _bad_words_cache[chat_id]
    with get_connection() as conn:
        if chat_id != 0:
            cur = conn.execute("SELECT DISTINCT word FROM custom_bad_words WHERE chat_id IN (?, 0)", (chat_id,))
        else:
            cur = conn.execute("SELECT DISTINCT word FROM custom_bad_words WHERE chat_id = 0")
        words = [row["word"] for row in cur.fetchall()]
        _bad_words_cache[chat_id] = words
        return words


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
    """Guruhda bot umumiy holati (yoqilgan/o'chirilgan) - RAM kesh: 0.0001ms."""
    if chat_id in _bot_status_cache:
        return _bot_status_cache[chat_id]
    with get_connection() as conn:
        cur = conn.execute("SELECT is_enabled FROM chat_bot_status WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if row is None:
            val = True
        else:
            val = bool(row["is_enabled"])
        _bot_status_cache[chat_id] = val
        return val


def set_bot_status(chat_id: int, enabled: bool):
    """Guruhda bot umumiy holatini yoqish yoki o'chirish."""
    _bot_status_cache[chat_id] = enabled
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


def get_chat_invite_link(chat_id: int) -> str | None:
    """Guruh taklif havolasini (invite_link) olish."""
    with get_connection() as conn:
        cur = conn.execute("SELECT invite_link, username FROM chats WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if row:
            if row["invite_link"] and str(row["invite_link"]).strip().startswith("http"):
                return str(row["invite_link"]).strip()
            if row["username"]:
                return f"https://t.me/{str(row['username']).lstrip('@').strip()}"
    return None


def set_chat_invite_link(chat_id: int, invite_link: str):
    """Guruh taklif havolasini bazaga yozish."""
    now_utc = datetime.now(timezone.utc)
    link_clean = invite_link.strip() if invite_link else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chats (chat_id, invite_link, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET invite_link = excluded.invite_link, updated_at = excluded.updated_at
            """,
            (chat_id, link_clean, now_utc)
        )
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


def get_user_managed_groups(user_id: int | str | None) -> list[dict]:
    """
    Foydalanuvchi boshqarishi mumkin bo'lgan guruhlar ro'yxati.
    - Agar bot egasi bo'lsa (@khojayev_ramz) yoki user_id berilmagan bo'lsa: barcha guruhlar ko'rinadi!
    - Agar muayyan admin bo'lsa: uning guruhlari, agar bo'lmasa barcha guruhlar chiqadi (hech qachon bo'sh qaytmaydi)!
    """
    all_groups = get_all_managed_groups()
    if user_id is not None:
        try:
            user_id = int(str(user_id).strip())
        except (ValueError, TypeError):
            pass

    if not user_id or user_id in BOT_OWNER_IDS:
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

    filtered = [g for g in all_groups if g["chat_id"] in auth_ids]
    if not filtered:
        return all_groups
    return filtered


def get_manager_overview() -> dict:
    """
    Faqat bot egasi (@khojayev_ramz) uchun:
    Barcha qo'shilgan guruhlar, ularning silkalari, a'zolari va bot holati haqida to'liq hisobot.
    """
    cutoff_24h_ts = int(time.time()) - (24 * 3600)
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
                (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.chat_id AND (unixepoch(m.created_at) >= ? OR datetime(m.created_at) >= datetime(?, 'unixepoch'))) AS msg_count_24h,
                c.updated_at
            FROM chats c
            LEFT JOIN chat_bot_status b ON c.chat_id = b.chat_id
            LEFT JOIN chat_censor_settings cs ON c.chat_id = cs.chat_id
            LEFT JOIN chat_stats_settings st ON c.chat_id = st.chat_id
            LEFT JOIN chat_game_settings gm ON c.chat_id = gm.chat_id
            WHERE c.chat_id < 0
            ORDER BY msg_count_24h DESC, c.updated_at DESC
        """, (cutoff_24h_ts, cutoff_24h_ts))
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
    cutoff_24h_ts = int(time.time()) - (24 * 3600)
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
                (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.chat_id AND (unixepoch(m.created_at) >= ? OR datetime(m.created_at) >= datetime(?, 'unixepoch'))) AS msg_count_24h
            FROM chats c
            LEFT JOIN chat_bot_status b ON c.chat_id = b.chat_id
            LEFT JOIN chat_censor_settings cs ON c.chat_id = cs.chat_id
            LEFT JOIN chat_stats_settings st ON c.chat_id = st.chat_id
            LEFT JOIN chat_game_settings gm ON c.chat_id = gm.chat_id
            WHERE c.chat_id < 0
            ORDER BY msg_count_24h DESC, c.updated_at DESC
        """, (cutoff_24h_ts, cutoff_24h_ts))
        rows = [dict(r) for r in cur.fetchall()]
        
        # Qachondir qo'shilgan, sozlamasi o'zgartirilgan yoki xabar yozilgan BARCHA guruhlarni to'plash:
        existing_ids = {r["chat_id"] for r in rows}
        cur_all = conn.execute("""
            SELECT DISTINCT chat_id FROM (
                SELECT chat_id FROM chats WHERE chat_id < 0
                UNION
                SELECT chat_id FROM messages WHERE chat_id < 0
                UNION
                SELECT chat_id FROM chat_settings WHERE chat_id < 0
                UNION
                SELECT chat_id FROM chat_bot_status WHERE chat_id < 0
                UNION
                SELECT chat_id FROM chat_game_settings WHERE chat_id < 0
                UNION
                SELECT chat_id FROM game_stats WHERE chat_id < 0
                UNION
                SELECT chat_id FROM chat_rules WHERE chat_id < 0
                UNION
                SELECT chat_id FROM chat_censor_settings WHERE chat_id < 0
                UNION
                SELECT chat_id FROM chat_stats_settings WHERE chat_id < 0
                UNION
                SELECT chat_id FROM warnings WHERE chat_id < 0
            )
        """)
        for r2 in cur_all.fetchall():
            cid = r2["chat_id"]
            if cid not in existing_ids:
                existing_ids.add(cid)
                t_row = conn.execute("SELECT title FROM chats WHERE chat_id = ?", (cid,)).fetchone()
                g_title = (t_row["title"] if t_row and t_row["title"] else None) or f"Guruh {cid}"
                conn.execute(
                    "INSERT INTO chats (chat_id, title, updated_at) VALUES (?, ?, ?) ON CONFLICT(chat_id) DO NOTHING",
                    (cid, g_title, datetime.now(timezone.utc))
                )
                conn.commit()
                rows.append({
                    "chat_id": cid,
                    "title": g_title,
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
    "anti_channel_enabled": 1,
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
    """Guruhning barcha sozlamalarini (mute/ban daqiqalari, flood, warn va h.k.) olish (RAM kesh: 0.0001ms)."""
    if chat_id in _chat_settings_cache:
        return dict(_chat_settings_cache[chat_id])
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        if not row:
            res = dict(DEFAULT_CHAT_SETTINGS)
            res["chat_id"] = chat_id
            _chat_settings_cache[chat_id] = res
            return dict(res)
        res = dict(row)
        if not res.get("welcome_text") or res.get("welcome_text") == "Assalomu alaykum, {name}! Guruhimizga xush kelibsiz!":
            res["welcome_text"] = DEFAULT_WELCOME_TEXT
        _chat_settings_cache[chat_id] = res
        return dict(res)


def update_chat_settings(chat_id: int, settings: dict):
    """Guruh sozlamalarini yangilash."""
    now_utc = datetime.now(timezone.utc)
    current = get_chat_full_settings(chat_id)
    current.update(settings)
    _chat_settings_cache[chat_id] = current
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO chat_settings (
                chat_id, censor_mute_seconds, censor_action,
                flood_msg_limit, flood_msg_window, flood_mute_seconds,
                flood_sticker_limit, flood_sticker_window, flood_sticker_mute_seconds,
                warn_limit, warn_action, warn_mute_seconds,
                link_filter_enabled, anti_channel_enabled, welcome_enabled, welcome_text, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                anti_channel_enabled = excluded.anti_channel_enabled,
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
            int(current.get("anti_channel_enabled", 1)),
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
            "top_users": top_users,
            "top_game_players": get_top_game_players(chat_id)
        }
    }


# -------------------------------------------------------------
# Hazil (Prank / Emoji / Ghost / Troll) Kesh va Baza funksiyalari
# -------------------------------------------------------------
_prank_users_cache: dict[tuple[int, int], dict] = {}       # (chat_id, user_id) -> {"mode": ..., "username": ..., "full_name": ...}
_prank_usernames_cache: dict[tuple[int, str], dict] = {}   # (chat_id, username_lower) -> {"mode": ..., "user_id": ..., "full_name": ...}


def init_prank_users_cache():
    """Bot ishga tushganda barcha faol hazil foydalanuvchilarini xotiraga (RAM) yuklash."""
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT chat_id, user_id, username, mode, full_name FROM prank_users")
            _prank_users_cache.clear()
            _prank_usernames_cache.clear()
            for row in cur.fetchall():
                cid = int(row["chat_id"])
                uid = int(row["user_id"] or 0)
                raw_u = str(row["username"] or "").strip()
                clean_u = raw_u.lstrip("@").strip().lower()
                mode = str(row["mode"] or "emoji").lower()
                full_name = str(row["full_name"] or "")

                info = {
                    "chat_id": cid,
                    "user_id": uid,
                    "username": clean_u,
                    "mode": mode,
                    "full_name": full_name
                }

                if uid > 0:
                    _prank_users_cache[(cid, uid)] = info
                if clean_u:
                    _prank_usernames_cache[(cid, clean_u)] = info
    except Exception as e:
        logger.error(f"init_prank_users_cache error: {e}")


def get_prank_user_action(chat_id: int, user_id: int, username: str | None = None) -> dict | None:
    """
    Foydalanuvchi Hazil (Prank) rejimida ekanligini tekshirish.
    1. RAM keshdan 0.0001ms da tekshiradi.
    2. Agar username orqali topilib, user_id 0 bo'lsa, xotira va bazada user_id ni muhrlaydi!
    3. Agar keshda topilmasa, SQLite bazasidan qidiradi va keshni yangilaydi.
    """
    clean_username = (username or "").lstrip("@").strip().lower()

    # 1. User ID bo'yicha RAM keshdan qidirish (Eng aniq va tezkor)
    if user_id and (chat_id, user_id) in _prank_users_cache:
        return _prank_users_cache[(chat_id, user_id)]

    # 2. Username bo'yicha RAM keshdan qidirish
    if clean_username and (chat_id, clean_username) in _prank_usernames_cache:
        info = _prank_usernames_cache[(chat_id, clean_username)]
        if user_id:
            info["user_id"] = user_id
            _prank_users_cache[(chat_id, user_id)] = info
            try:
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE prank_users SET user_id = ? WHERE chat_id = ? AND (LOWER(REPLACE(username, '@', '')) = ? OR username = ?) AND (user_id = 0 OR user_id IS NULL)",
                        (user_id, chat_id, clean_username, str(user_id))
                    )
                    conn.commit()
            except Exception:
                pass
        return info

    # 3. Agar RAM keshda bo'lmasa -> Baza (SQLite) orqali tekshirish
    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                SELECT chat_id, user_id, username, mode, full_name 
                FROM prank_users 
                WHERE chat_id = ? AND (
                    (user_id > 0 AND user_id = ?) 
                    OR (username != '' AND (
                        LOWER(REPLACE(username, '@', '')) = ? 
                        OR LOWER(username) = ? 
                        OR username = ?
                    ))
                )
                LIMIT 1
                """,
                (chat_id, user_id or 0, clean_username, clean_username, str(user_id) if user_id else "")
            )
            row = cur.fetchone()
            if row:
                info = {
                    "chat_id": int(row["chat_id"]),
                    "user_id": int(row["user_id"] or 0),
                    "username": str(row["username"] or ""),
                    "mode": str(row["mode"] or "emoji").lower(),
                    "full_name": str(row["full_name"] or "")
                }
                if user_id:
                    info["user_id"] = user_id
                    _prank_users_cache[(chat_id, user_id)] = info
                    if int(row["user_id"] or 0) == 0:
                        conn.execute(
                            "UPDATE prank_users SET user_id = ? WHERE chat_id = ? AND username = ?",
                            (user_id, chat_id, row["username"])
                        )
                        conn.commit()
                if clean_username:
                    _prank_usernames_cache[(chat_id, clean_username)] = info
                return info
    except Exception as e:
        logger.error(f"get_prank_user_action db fallback error: {e}")

    return None


def is_prank_user(chat_id: int, user_id: int | None = None, username: str | None = None) -> bool:
    """Eski kodlar uchun moslik: foydalanuvchi hazildami tekshirish."""
    return get_prank_user_action(chat_id, user_id or 0, username) is not None


def resolve_member_identity(chat_id: int, target: str) -> tuple[int, str, str]:
    """
    Foydalanuvchini 100% aniqlik bilan aniqlash:
    1. Telegram Bot API: jonli getChatAdministrators tekshiruvi (Adminlar uchun 100% aniqlik)
    2. Agar to'g'ridan-to'g'ri User ID raqam bo'lsa -> known_users / Telegram API getChatMember
    3. Username yoki ism bo'lsa -> known_users va messages dan qidiradi
    """
    clean_target = str(target).strip()
    for prefix in ("id:", "id ", "id-", "user_id:", "@"):
        if clean_target.lower().startswith(prefix):
            clean_target = clean_target[len(prefix):].strip()

    clean_name = clean_target.lower()

    # 1. Telegram Bot API: jonli getChatAdministrators tekshiruvi (Adminlar uchun 100% aniqlik)
    try:
        from group_bot.config import BOT_TOKEN
        import urllib.request, json
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatAdministrators?chat_id={chat_id}"
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                for admin in data.get("result", []):
                    u = admin.get("user", {})
                    u_id = int(u.get("id", 0))
                    u_uname = (u.get("username") or "").lower()
                    u_fname = (u.get("first_name") or "") + (" " + u.get("last_name") if u.get("last_name") else "")
                    u_fname_clean = u_fname.strip().lower()
                    fname_parts = [p for p in u_fname_clean.split() if len(p) >= 2]

                    if (
                        (u_uname and clean_name == u_uname)
                        or clean_name == str(u_id)
                        or (u_fname_clean and clean_name == u_fname_clean)
                        or any(clean_name == part for part in fname_parts)
                    ):
                        upsert_known_user(u_id, u_fname.strip() or f"Admin {u_id}", u_uname, chat_id)
                        return u_id, u_uname, u_fname.strip() or f"Admin {u_id}"
    except Exception as e:
        logger.warning(f"resolve_member_identity Telegram getChatAdministrators error: {e}")

    # 2. Agar to'g'ridan-to'g'ri User ID raqam bo'lsa
    if clean_target.isdigit():
        uid = int(clean_target)
        known = get_user_by_id(uid)
        if known and known.get("full_name"):
            return uid, (known.get("username") or "").lower(), known.get("full_name")
        # Jonli Telegram getChatMember orqali tekshirish
        try:
            from group_bot.config import BOT_TOKEN
            import urllib.request, json
            api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={chat_id}&user_id={uid}"
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    u = data.get("result", {}).get("user", {})
                    u_uname = (u.get("username") or "").lower()
                    u_fname = (u.get("first_name") or "") + (" " + u.get("last_name") if u.get("last_name") else "")
                    upsert_known_user(uid, u_fname.strip() or f"User {uid}", u_uname, chat_id)
                    return uid, u_uname, u_fname.strip() or f"User {uid}"
        except Exception:
            pass
        return uid, "", f"ID {uid}"

    # 3. known_users va messages dan tekshirish
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT user_id, username, full_name FROM known_users 
            WHERE last_chat_id = ? AND (
                LOWER(REPLACE(username, '@', '')) = ? 
                OR LOWER(full_name) = ?
            ) LIMIT 1
            """,
            (chat_id, clean_name, clean_name)
        )
        row = cur.fetchone()
        if not row:
            cur = conn.execute(
                """
                SELECT user_id, username, full_name FROM known_users 
                WHERE LOWER(REPLACE(username, '@', '')) = ? OR LOWER(full_name) = ? LIMIT 1
                """,
                (clean_name, clean_name)
            )
            row = cur.fetchone()
        if not row:
            cur = conn.execute(
                """
                SELECT user_id, username, full_name FROM messages 
                WHERE chat_id = ? AND (
                    LOWER(REPLACE(username, '@', '')) = ? 
                    OR LOWER(full_name) = ?
                ) ORDER BY id DESC LIMIT 1
                """,
                (chat_id, clean_name, clean_name)
            )
            row = cur.fetchone()
        if row:
            return int(row["user_id"]), (row["username"] or "").lower(), row["full_name"] or clean_target

    return 0, clean_name, f"@{clean_name}"


def add_prank_user(chat_id: int, target: str, mode: str = "emoji") -> tuple[bool, str]:
    """
    Hazil rejimiga foydalanuvchi qo'shish (ko'pi bilan 5 ta).
    mode: 'emoji' (Emoji Bomb), 'ghost' (Arvoh), 'mute' (Super Mute), 'troll' (Masxarachi), 'chaos' (Aralash)
    """
    raw_target = str(target).strip()
    if not raw_target:
        return False, "Username yoki User ID kiritilmadi!"

    valid_modes = {"emoji", "ghost", "mute", "troll", "chaos"}
    clean_mode = mode.lower().strip() if mode else "emoji"
    if clean_mode not in valid_modes:
        clean_mode = "emoji"

    uid, clean_username, full_name = resolve_member_identity(chat_id, raw_target)
    display_label = f"{full_name} (@{clean_username})" if clean_username else (f"{full_name} (ID: {uid})" if uid > 0 else f"@{clean_username}")
    identifier = clean_username or str(uid)

    with get_connection() as conn:
        cur = conn.execute("SELECT count(*) as cnt FROM prank_users WHERE chat_id = ?", (chat_id,))
        count = cur.fetchone()["cnt"]

        # Allaqachon bormi tekshirish
        cur = conn.execute(
            """
            SELECT 1 FROM prank_users 
            WHERE chat_id = ? AND (
                (user_id > 0 AND user_id = ?) 
                OR (username != '' AND (username = ? OR username = ? OR LOWER(username) = ?))
            )
            """,
            (chat_id, uid, identifier, f"@{identifier}", identifier.lower())
        )
        existing = cur.fetchone()
        if existing:
            # Rejimini yangilash
            conn.execute(
                """
                UPDATE prank_users 
                SET mode = ?, 
                    user_id = CASE WHEN user_id = 0 THEN ? ELSE user_id END, 
                    full_name = ? 
                WHERE chat_id = ? AND (
                    (user_id > 0 AND user_id = ?) 
                    OR (username != '' AND (username = ? OR username = ? OR LOWER(username) = ?))
                )
                """,
                (clean_mode, uid, full_name, chat_id, uid, identifier, f"@{identifier}", identifier.lower())
            )
            conn.commit()
            init_prank_users_cache()
            mode_name = {"emoji": "💩 Emoji Bomb", "ghost": "👻 Ghost", "mute": "🔇 Super Mute", "troll": "🤡 Troll", "chaos": "🎲 Chaos"}.get(clean_mode, clean_mode)
            return True, f"{display_label} rejimi {mode_name} ga o'zgartirildi!"

        if count >= 5:
            return False, "Maksimal 5 ta foydalanuvchi kiritish mumkin!"

        conn.execute(
            """
            INSERT INTO prank_users (chat_id, username, user_id, mode, full_name)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, username) DO UPDATE SET
                user_id = excluded.user_id,
                mode = excluded.mode,
                full_name = excluded.full_name
            """,
            (chat_id, identifier, uid, clean_mode, full_name)
        )
        conn.commit()

    init_prank_users_cache()
    mode_name = {"emoji": "💩 Emoji Bomb", "ghost": "👻 Ghost", "mute": "🔇 Super Mute", "troll": "🤡 Troll", "chaos": "🎲 Chaos"}.get(clean_mode, clean_mode)
    return True, f"{display_label} Hazil ({mode_name}) rejimiga qo'shildi!"


def remove_prank_user(chat_id: int, target: str) -> bool:
    """Hazil rejimidan username yoki User ID ni o'chirish."""
    raw_target = str(target).strip()
    clean_target = raw_target.lower()
    for prefix in ("id:", "id ", "id-", "user_id:", "@"):
        if clean_target.startswith(prefix):
            clean_target = clean_target[len(prefix):].strip()

    uid = int(clean_target) if clean_target.isdigit() else 0
    clean_uname = clean_target.lstrip("@").strip().lower()

    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM prank_users
            WHERE chat_id = ? AND (
                LOWER(username) = ? 
                OR LOWER(REPLACE(username, '@', '')) = ?
                OR username = ? 
                OR (user_id > 0 AND user_id = ?)
                OR (? > 0 AND username = ?)
            )
            """,
            (chat_id, clean_uname, clean_uname, raw_target, uid, uid, str(uid))
        )
        conn.commit()

    init_prank_users_cache()
    return True


def get_prank_users(chat_id: int) -> list[dict]:
    """Guruhdagi barcha hazil rejimidagi foydalanuvchilar ma'lumotlarini olish."""
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT chat_id, user_id, username, mode, full_name, created_at FROM prank_users WHERE chat_id = ? ORDER BY created_at ASC",
            (chat_id,)
        )
        return [dict(row) for row in cur.fetchall()]


def log_user_punishment(chat_id: int, user_id: int, action_type: str, reason: str = "", duration_seconds: int = 0):
    """Foydalanuvchi jazolanganini (mute, virtual_mute, warn, ban va h.k.) bazaga qayd etish."""
    now_uzb_str = get_uzb_now_str()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_punishments (chat_id, user_id, action_type, reason, duration_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, action_type, reason, duration_seconds, now_uzb_str)
        )
        conn.commit()


def get_user_punishments_count(chat_id: int, user_id: int) -> int:
    """Foydalanuvchi shu guruhda necha marta mute/jazo olganini hisoblash."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT count(*) as cnt 
            FROM user_punishments 
            WHERE chat_id = ? AND user_id = ? AND action_type IN ('mute', 'virtual_mute')
            """,
            (chat_id, user_id)
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0


def record_member_join(chat_id: int, user_id: int, full_name: str, username: str | None = None, is_exact: bool = False):
    """A'zo guruhga qo'shilgan vaqtini qayd etish."""
    now_uzb_str = get_uzb_now_str()
    is_exact_val = 1 if is_exact else 0
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO group_members (chat_id, user_id, full_name, username, joined_at, first_seen, last_seen, is_exact_join, total_messages)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = COALESCE(excluded.username, group_members.username),
                last_seen = excluded.last_seen,
                is_exact_join = MAX(group_members.is_exact_join, excluded.is_exact_join)
            """,
            (chat_id, user_id, full_name, username, now_uzb_str, now_uzb_str, now_uzb_str, is_exact_val)
        )
        conn.commit()


def get_user_info_stats(chat_id: int, user_id: int) -> dict:
    """
    Foydalanuvchining to'liq hisoboti (.info buyrug'i uchun):
    - Guruhga qachon qo'shilgan / birinchi ko'rilgan
    - Necha marta mute olgani (jami va so'nggi 24 soat)
    - Qo'shilganidan beri jami qancha xabar yozgani
    - 24 soatlik xabarlari (O'zbekiston vaqti bo'yicha aniq 24 soat)
    - Ogohlantirishlari
    - Hazil (Ghost) rejimi holati
    """
    cutoff_24h_ts = int(time.time()) - (24 * 3600)
    with get_connection() as conn:
        # 1. messages jadvalidan umumiy xabarlar va birinchi/oxirgi xabar vaqti
        cur = conn.execute(
            """
            SELECT count(*) as total, min(created_at) as first_msg, max(created_at) as last_msg
            FROM messages
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id)
        )
        msg_row = cur.fetchone()
        table_msgs = msg_row["total"] if msg_row else 0
        first_msg = msg_row["first_msg"] if msg_row else None
        last_msg = msg_row["last_msg"] if msg_row else None

        # 2. 24 soatlik xabarlar soni (O'zbekiston vaqti bo'yicha aniq 24 soat)
        cur = conn.execute(
            """
            SELECT count(*) as cnt_24h 
            FROM messages 
            WHERE chat_id = ? AND user_id = ? 
              AND (unixepoch(created_at) >= ? OR datetime(created_at) >= datetime(?, 'unixepoch'))
            """,
            (chat_id, user_id, cutoff_24h_ts, cutoff_24h_ts)
        )
        msgs_24h = cur.fetchone()["cnt_24h"]

        # 3. Qo'shilgan vaqti (group_members yoki birinchi xabar vaqti)
        cur = conn.execute(
            "SELECT joined_at, first_seen, last_seen, full_name, username, is_exact_join, total_messages FROM group_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        m_row = cur.fetchone()
        joined_at = None
        is_exact = False
        member_total = 0
        if m_row:
            joined_at = m_row["joined_at"]
            try:
                is_exact = bool(m_row["is_exact_join"])
            except Exception:
                is_exact = False
            try:
                member_total = int(m_row["total_messages"] or 0)
            except Exception:
                member_total = 0
        elif first_msg:
            joined_at = first_msg
        else:
            cur = conn.execute("SELECT updated_at FROM known_users WHERE user_id = ?", (user_id,))
            k_row = cur.fetchone()
            if k_row and k_row["updated_at"]:
                joined_at = k_row["updated_at"]

        # Jami barcha xabarlar soni
        total_msgs = max(member_total, table_msgs)

        # 4. Mute jazolari soni (umumiy va 24 soatlik O'zbekiston vaqti)
        cur = conn.execute(
            """
            SELECT count(*) as mute_cnt 
            FROM user_punishments 
            WHERE chat_id = ? AND user_id = ? AND action_type IN ('mute', 'virtual_mute')
            """,
            (chat_id, user_id)
        )
        mute_cnt = cur.fetchone()["mute_cnt"]

        cur = conn.execute(
            """
            SELECT count(*) as mute_24h 
            FROM user_punishments 
            WHERE chat_id = ? AND user_id = ? 
              AND action_type IN ('mute', 'virtual_mute') 
              AND (unixepoch(created_at) >= ? OR datetime(created_at) >= datetime(?, 'unixepoch'))
            """,
            (chat_id, user_id, cutoff_24h_ts, cutoff_24h_ts)
        )
        mute_24h = cur.fetchone()["mute_24h"]

        # 5. Faol ogohlantirishlar
        cur = conn.execute("SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        w_row = cur.fetchone()
        warn_cnt = w_row["count"] if w_row else 0

        # 6. Profil ma'lumotlari
        known = get_user_by_id(user_id)
        full_name = (known.get("full_name") if known else None) or (m_row["full_name"] if m_row else f"Foydalanuvchi {user_id}")
        username = (known.get("username") if known else None) or (m_row["username"] if m_row else None)

        # 7. Ghost holati
        ghost_active = is_prank_user(chat_id, user_id=user_id, username=username)

        # 8. Virtual mute holati
        virt_muted = is_admin_virtually_muted(chat_id, user_id)

        return {
            "user_id": user_id,
            "full_name": full_name,
            "username": username,
            "joined_at": joined_at,
            "is_exact_join": is_exact,
            "first_msg": first_msg,
            "last_msg": last_msg or (m_row["last_seen"] if m_row else None),
            "total_msgs": total_msgs,
            "msgs_24h": msgs_24h,
            "mute_count": mute_cnt,
            "mute_24h": mute_24h,
            "warn_count": warn_cnt,
            "is_ghost": ghost_active,
            "is_virtually_muted": virt_muted
        }


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
    now_uzb_str = get_uzb_now_str()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO admin_virtual_mutes (chat_id, user_id, until_ts, duration_seconds, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                until_ts = excluded.until_ts,
                duration_seconds = excluded.duration_seconds,
                created_at = excluded.created_at
        """, (chat_id, user_id, until_ts, duration_seconds, now_uzb_str))
        conn.commit()
    log_user_punishment(chat_id, user_id, action_type="virtual_mute", reason="Admin Virtual Mute", duration_seconds=duration_seconds)
    return until_ts


def remove_admin_virtual_mute(chat_id: int, user_id: int) -> bool:
    """Adminni virtual mutedan chiqarish."""
    _admin_virtual_mutes_cache.pop((chat_id, user_id), None)
    with get_connection() as conn:
        conn.execute("DELETE FROM admin_virtual_mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()
    return True


def is_admin_virtually_muted(chat_id: int, user_id: int) -> bool:
    """Admin ayni damda virtual mutedami (O(1) kesh tekshiruv, bazaga avto-fallback bilan)."""
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

    # Keshda bo'lmasa, bazadan tekshirish (server restart yoki kesh yangilanishida yo'qolmasligi uchun)
    try:
        with get_connection() as conn:
            row = conn.execute("SELECT until_ts FROM admin_virtual_mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)).fetchone()
            if row:
                db_until = float(row["until_ts"])
                if now < db_until:
                    _admin_virtual_mutes_cache[(chat_id, user_id)] = db_until
                    return True
                else:
                    conn.execute("DELETE FROM admin_virtual_mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
                    conn.commit()
                    return False
    except Exception:
        pass

    return False


def get_admin_virtual_mute_remaining(chat_id: int, user_id: int) -> int | None:
    """Adminning qolgan mute soniyalarini olish."""
    now = time.time()
    until_ts = _admin_virtual_mutes_cache.get((chat_id, user_id))
    if until_ts and until_ts > now:
        return int(until_ts - now)

    try:
        with get_connection() as conn:
            row = conn.execute("SELECT until_ts FROM admin_virtual_mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id)).fetchone()
            if row:
                db_until = float(row["until_ts"])
                if db_until > now:
                    _admin_virtual_mutes_cache[(chat_id, user_id)] = db_until
                    return int(db_until - now)
    except Exception:
        pass

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
        upsert_known_user(winner_id, winner_name, winner_uname, chat_id)
        upsert_known_user(loser_id, loser_name, loser_uname, chat_id)
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


def set_user_game_wins(
    chat_id: int,
    user_id: int,
    wins: int,
    full_name: str | None = None,
    username: str | None = None
) -> int:
    """Foydalanuvchining g'alabalar sonini to'g'ridan-to'g'ri o'rnatish (Admin uchun)."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        if not full_name:
            cur = conn.execute("SELECT full_name, username FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
            row = cur.fetchone()
            if row:
                full_name = row["full_name"]
                username = row["username"] or username
            else:
                full_name = username or f"User {user_id}"

        conn.execute("""
            INSERT INTO game_stats (chat_id, user_id, full_name, username, wins, losses, total_games, claimed_milestones, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, '', ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = COALESCE(excluded.full_name, full_name),
                username = COALESCE(excluded.username, username),
                wins = excluded.wins,
                total_games = MAX(total_games, excluded.wins),
                updated_at = excluded.updated_at
        """, (chat_id, user_id, full_name, username, wins, wins, now))
        conn.commit()
    upsert_known_user(user_id, full_name, username, chat_id)
    return wins


def get_user_id_by_username_global(username: str) -> dict | None:
    """Butun bazadan username bo'yicha user_id va full_name topish (Super-tergov waterfall)."""
    return get_user_by_username(0, username)


# -------------------------------------------------------------
# Teg Berish Huquqiga Ega Foydalanuvchilar (Authorized Taggers)
# -------------------------------------------------------------
_authorized_taggers_cache: dict[int, dict] = {}
_authorized_taggers_uname_cache: dict[str, int] = {}


def init_authorized_taggers_cache():
    """Bot ishga tushganda ruxsat berilgan taggerlarni xotiraga yuklash."""
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT user_id, username, full_name, added_by, created_at FROM authorized_taggers")
            _authorized_taggers_cache.clear()
            _authorized_taggers_uname_cache.clear()
            for row in cur.fetchall():
                uid = int(row["user_id"])
                uname = (row["username"] or "").lstrip("@").strip().lower()
                data = {
                    "user_id": uid,
                    "username": row["username"],
                    "full_name": row["full_name"],
                    "added_by": row["added_by"],
                    "created_at": str(row["created_at"] or "")
                }
                _authorized_taggers_cache[uid] = data
                if uname:
                    _authorized_taggers_uname_cache[uname] = uid
    except Exception as e:
        logger.error(f"init_authorized_taggers_cache error: {e}")


def add_authorized_tagger(user_id: int, username: str | None = None, full_name: str | None = None, added_by: int | None = None) -> bool:
    """Teg berish huquqiga ega yangi foydalanuvchi qo'shish."""
    clean_u = (username or "").lstrip("@").strip()
    f_name = full_name or (f"@{clean_u}" if clean_u else f"Foydalanuvchi {user_id}")
    now_str = get_uzb_now_str()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO authorized_taggers (user_id, username, full_name, added_by, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, username),
                full_name = COALESCE(excluded.full_name, full_name),
                added_by = excluded.added_by,
                created_at = excluded.created_at
        """, (user_id, clean_u, f_name, added_by, now_str))
        conn.commit()

    info = {
        "user_id": user_id,
        "username": clean_u,
        "full_name": f_name,
        "added_by": added_by,
        "created_at": now_str
    }
    _authorized_taggers_cache[user_id] = info
    if clean_u:
        _authorized_taggers_uname_cache[clean_u.lower()] = user_id
    return True


def remove_authorized_tagger(user_id: int) -> bool:
    """Teg berish huquqidan mahrum qilish."""
    info = _authorized_taggers_cache.pop(user_id, None)
    if info and info.get("username"):
        _authorized_taggers_uname_cache.pop(info["username"].lower(), None)

    with get_connection() as conn:
        conn.execute("DELETE FROM authorized_taggers WHERE user_id = ?", (user_id,))
        conn.commit()
    return True


def get_all_authorized_taggers() -> list[dict]:
    """Barcha ruxsat berilgan taggerlar ro'yxatini olish."""
    if not _authorized_taggers_cache:
        init_authorized_taggers_cache()
    return list(_authorized_taggers_cache.values())


def is_user_authorized_tagger(user_id: int | None, username: str | None = None) -> bool:
    """Foydalanuvchi teg berishga ruxsat etilganmi."""
    if not user_id and not username:
        return False

    # 1. Asosiy bot egalari (@khojayev_ramz, @wdablyu) doim ruxsatga ega
    if user_id and (user_id in BOT_OWNER_IDS or user_id in (8594505572, 7690283463)):
        return True
    clean_u = (username or "").lstrip("@").strip().lower()
    if clean_u in ("khojayev_ramz", "wdablyu"):
        return True

    # 2. Qo'shilgan vakillar keshidan tekshirish
    if user_id and user_id in _authorized_taggers_cache:
        return True
    if clean_u and clean_u in _authorized_taggers_uname_cache:
        return True

    # 3. Keshda bo'lmasa, bazadan tekshirish
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                SELECT user_id, username, full_name, added_by, created_at
                FROM authorized_taggers
                WHERE user_id = ? OR (username != '' AND LOWER(username) = ?)
                LIMIT 1
            """, (user_id or 0, clean_u))
            row = cur.fetchone()
            if row:
                uid = int(row["user_id"])
                _authorized_taggers_cache[uid] = dict(row)
                if row["username"]:
                    _authorized_taggers_uname_cache[row["username"].lower()] = uid
                return True
    except Exception:
        pass

    return False


# Auto-initialize database schema and caches on module import so tables always exist immediately
try:
    init_db()
    init_authorized_taggers_cache()
except Exception:
    pass





