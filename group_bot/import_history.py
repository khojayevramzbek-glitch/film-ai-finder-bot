import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "bot_data.db"


def import_telegram_export(json_path: str, target_chat_id: int = -1003834509976):
    """
    Telegram Desktop JSON eksport faylidan barcha a'zolar xabarlari va
    qo'shilgan sanalarini bot bazasiga to'liq yuklash (Import).
    """
    path = Path(json_path)
    if not path.exists():
        print(f"Fayl topilmadi: {json_path}")
        return False

    print(f"Fayl ochilmoqda: {path}...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = []
    # 1. Agar to'g'ridan-to'g'ri guruh eksporti bo'lsa (messages.json yoki bitta chat)
    if "messages" in data and isinstance(data["messages"], list):
        messages = data["messages"]
    # 2. Agar umumiy akkaunt eksporti bo'lsa (result.json -> chats -> list)
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

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row

    users_stats = {}  # user_id -> {full_name, username, first_date, last_date, msg_count}
    db_messages = []

    for m in messages:
        m_id = m.get("id")
        date_str = m.get("date")
        if not date_str:
            continue

        # from_id ni aniqlash: "user8594505572" -> 8594505572
        raw_from_id = m.get("from_id") or m.get("actor_id")
        if not raw_from_id or not str(raw_from_id).startswith("user"):
            continue

        try:
            user_id = int(str(raw_from_id).replace("user", ""))
        except Exception:
            continue

        full_name = m.get("from") or m.get("actor") or f"User {user_id}"
        username = None  # JSON exportda odatda username bo'lmaydi, lekin known_users orqali saqlanadi

        # Format date
        try:
            dt = datetime.fromisoformat(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            iso_date = dt.isoformat()
        except Exception:
            iso_date = date_str

        # Statistika yig'ish
        if user_id not in users_stats:
            users_stats[user_id] = {
                "full_name": full_name,
                "username": username,
                "first_date": iso_date,
                "last_date": iso_date,
                "msg_count": 0
            }

        users_stats[user_id]["msg_count"] += 1
        users_stats[user_id]["last_date"] = iso_date
        if iso_date < users_stats[user_id]["first_date"]:
            users_stats[user_id]["first_date"] = iso_date

        if m.get("type") == "message":
            db_messages.append((m_id, target_chat_id, user_id, full_name, username, iso_date))

    print(f"Topilgan a'zolar soni: {len(users_stats)}")
    for uid, st in users_stats.items():
        print(f"👤 {st['full_name']} (ID: {uid}): {st['msg_count']} ta xabar, Birinchi faolligi: {st['first_date']}")

    # Bazaga guruh a'zolarini va birinchi faollik sanasini yozish
    for uid, st in users_stats.items():
        conn.execute("""
            INSERT INTO group_members (chat_id, user_id, full_name, username, joined_at, first_seen, last_seen, is_exact_join)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                full_name = excluded.full_name,
                joined_at = MIN(group_members.joined_at, excluded.joined_at),
                first_seen = MIN(group_members.first_seen, excluded.first_seen),
                last_seen = MAX(group_members.last_seen, excluded.last_seen),
                is_exact_join = 1
        """, (target_chat_id, uid, st["full_name"], st["username"], st["first_date"], st["first_date"], st["last_date"]))

        conn.execute("""
            INSERT INTO known_users (user_id, username, full_name, last_chat_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                last_chat_id = excluded.last_chat_id,
                updated_at = excluded.updated_at
        """, (uid, st["username"], st["full_name"], target_chat_id, st["last_date"]))

    # Xabarlarni bazaga to'ldirish (agar mavjud bo'lmasa)
    print(f"{len(db_messages)} ta xabar bazaga kiritilmoqda...")
    conn.executemany("""
        INSERT OR IGNORE INTO messages (message_id, chat_id, user_id, full_name, username, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, db_messages)

    conn.commit()
    conn.close()
    print("✅ Eksport ma'lumotlari muvaffaqiyatli bazaga yuklandi!")
    return True


if __name__ == "__main__":
    import sys
    path = r"C:\Users\Ramzbek\Downloads\Telegram Desktop\DataExport_2026-10-01 (1)\result.json"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    import_telegram_export(path)
