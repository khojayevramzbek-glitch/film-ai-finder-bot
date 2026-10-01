import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "bot_data.db"


def import_telegram_export(export_path: str, target_chat_id: int = -1003834509976):
    """
    Telegram Desktop JSON eksport faylidan barcha a'zolar xabarlari va
    qo'shilgan sanalarini bot bazasiga to'liq yuklash (Import).
    """
    path = Path(export_path)
    if path.is_dir():
        path = path / "result.json"

    if not path.exists():
        print(f"Fayl topilmadi: {path}")
        return False

    print(f"Fayl ochilmoqda: {path}...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = []
    # 1. To'g'ridan-to'g'ri bitta guruh eksporti (result.json -> messages)
    if "messages" in data and isinstance(data["messages"], list):
        messages = data["messages"]
        print(f"Guruh nomi: {data.get('name')} (ID: {data.get('id')})")
    # 2. Butun akkaunt eksporti (result.json -> chats -> list)
    elif "chats" in data and "list" in data["chats"]:
        target_str = str(abs(target_chat_id)).replace("100", "", 1) if str(abs(target_chat_id)).startswith("100") else str(abs(target_chat_id))
        for c in data["chats"]["list"]:
            cid_str = str(c.get("id", ""))
            name_str = str(c.get("name", "")).lower()
            if cid_str == target_str or "3834509976" in cid_str or "близкий" in name_str:
                messages = c.get("messages", [])
                print(f"Guruh topildi: {c.get('name')} (ID: {c.get('id')}), xabarlar soni: {len(messages)}")
                break

    if not messages:
        print("Xabarlar topilmadi!")
        return False

    print(f"Jami tahlil qilinadigan xabarlar soni: {len(messages)}")

    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.row_factory = sqlite3.Row

    # Jadval ustunlari mavjudligini kafolatlash
    try:
        conn.execute("ALTER TABLE group_members ADD COLUMN is_exact_join INTEGER DEFAULT 0;")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE group_members ADD COLUMN total_messages INTEGER DEFAULT 0;")
    except Exception:
        pass

    users_stats = {}  # user_id -> {full_name, username, join_date, first_seen, last_seen, msg_count}
    recent_messages = []
    max_ts = 0

    # 1-qadam: Eng so'nggi xabar vaqtini aniqlash (so'nggi 3 kunlik xabarlarni ajratib olish uchun)
    for m in messages:
        ts = m.get("date_unixtime")
        if ts and int(ts) > max_ts:
            max_ts = int(ts)

    cutoff_3d_ts = max_ts - (3 * 86400) if max_ts > 0 else 0

    # 2-qadam: Barcha xabarlarni bir marta to'liq tahlil qilish
    for m in messages:
        m_id = m.get("id")
        date_unixtime = m.get("date_unixtime")
        date_str = m.get("date")

        if date_unixtime:
            dt = datetime.fromtimestamp(int(date_unixtime), timezone.utc)
            iso_date = dt.isoformat()
            ts_val = int(date_unixtime)
        elif date_str:
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                iso_date = dt.isoformat()
                ts_val = int(dt.timestamp())
            except Exception:
                iso_date = date_str
                ts_val = 0
        else:
            continue

        raw_from_id = m.get("from_id") or m.get("actor_id")
        if not raw_from_id or not str(raw_from_id).startswith("user"):
            continue

        try:
            user_id = int(str(raw_from_id).replace("user", ""))
        except Exception:
            continue

        name = m.get("from") or m.get("actor") or f"User {user_id}"
        m_type = m.get("type")
        act = m.get("action")

        if user_id not in users_stats:
            users_stats[user_id] = {
                "full_name": name,
                "username": None,
                "join_date": None,
                "first_seen": iso_date,
                "last_seen": iso_date,
                "msg_count": 0
            }

        st = users_stats[user_id]
        if name and not st["full_name"].startswith("User "):
            st["full_name"] = name

        if iso_date < st["first_seen"]:
            st["first_seen"] = iso_date
        if iso_date > st["last_seen"]:
            st["last_seen"] = iso_date

        if act == "join_group_by_request":
            if not st["join_date"] or iso_date < st["join_date"]:
                st["join_date"] = iso_date

        if m_type == "message":
            st["msg_count"] += 1
            if ts_val >= cutoff_3d_ts:
                recent_messages.append((m_id, target_chat_id, user_id, name, None, iso_date))

    print(f"Tahlil qilindi: {len(users_stats)} nafar unikal a'zo aniqlandi.")

    # 3-qadam: group_members va known_users jadvallarini yangilash
    print("A'zolar ma'lumotlari bazaga yozilmoqda...")
    for uid, st in users_stats.items():
        # Agar join_group_by_request bo'lmasa, uning ilk faolligi (birinchi xabari) qo'shilgan vaqti hisoblanadi
        effective_join = st["join_date"] or st["first_seen"]

        conn.execute("""
            INSERT INTO group_members (chat_id, user_id, full_name, username, joined_at, first_seen, last_seen, is_exact_join, total_messages)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = COALESCE(excluded.username, group_members.username),
                joined_at = MIN(group_members.joined_at, excluded.joined_at),
                first_seen = MIN(group_members.first_seen, excluded.first_seen),
                last_seen = MAX(group_members.last_seen, excluded.last_seen),
                is_exact_join = 1,
                total_messages = MAX(COALESCE(group_members.total_messages, 0), excluded.total_messages)
        """, (target_chat_id, uid, st["full_name"], st["username"], effective_join, st["first_seen"], st["last_seen"], st["msg_count"]))

        conn.execute("""
            INSERT INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                last_chat_id = excluded.last_chat_id,
                updated_at = excluded.updated_at
        """, (uid, st["username"], st["full_name"], target_chat_id, st["last_seen"]))

    # 4-qadam: So'nggi 3 kunlik xabarlarni messages jadvaliga kiritish (24 soatlik statistika uchun)
    print(f"So'nggi 3 kunlik {len(recent_messages)} ta xabar 'messages' jadvaliga kiritilmoqda...")
    conn.executemany("""
        INSERT OR IGNORE INTO messages (message_id, chat_id, user_id, full_name, username, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, recent_messages)

    conn.commit()

    # Bazani optimizatsiya qilish
    print("Baza optimallashtirilmoqda (VACUUM & ANALYZE)...")
    conn.execute("ANALYZE;")
    conn.commit()
    conn.close()

    print("✅ Tarixiy eksport ma'lumotlari to'liq va muvaffaqiyatli yuklandi!")
    return True


if __name__ == "__main__":
    path = r"C:\Users\Ramzbek\Downloads\Telegram Desktop\ChatExport_2026-10-01 (1)\result.json"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    import_telegram_export(path)
