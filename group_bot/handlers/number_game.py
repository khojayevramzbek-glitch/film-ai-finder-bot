import asyncio
import random
import re
import time
import uuid
from html import escape
from typing import Dict

from aiogram import Router, types, Bot, F
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

try:
    from group_bot import database as group_db
    from group_bot.database import (
        get_user_by_username, get_user_by_id,
        record_game_result, get_user_game_stats, get_top_game_players
    )
except ImportError:
    import database as group_db
    from database import (
        get_user_by_username, get_user_by_id,
        record_game_result, get_user_game_stats, get_top_game_players
    )

router = Router()

# Telegram Gift Sovg'alari Marralari:
GIFT_MILESTONES = {
    30: {"name": "Telegram Gift (Quti)", "stars": 25, "icon": "🎁"},
    50: {"name": "Telegram Gift (Raketa)", "stars": 50, "icon": "🚀"},
    100: {"name": "Telegram Gift (Oltin Kubok)", "stars": 100, "icon": "🏆"}
}
BOT_OWNER_NOTIFY_IDS = [8594505572, 7690283463]


class GameState:
    def __init__(
        self,
        game_id: str,
        chat_id: int,
        p1_id: int,
        p1_name: str,
        p1_username: str | None,
        p2_id: int,
        p2_name: str,
        p2_username: str | None
    ):
        self.game_id = game_id
        self.chat_id = chat_id
        self.p1_id = p1_id
        self.p1_name = p1_name
        self.p1_username = p1_username
        self.p2_id = p2_id
        self.p2_name = p2_name
        self.p2_username = p2_username

        self.status = "invited"  # invited -> range_select -> picking -> playing -> finished
        self.max_range = 100
        self.p1_secret: int | None = None
        self.p2_secret: int | None = None
        self.turn_user_id: int = p1_id

        self.p1_min = 1
        self.p1_max = 100
        self.p2_min = 1
        self.p2_max = 100

        self.p1_attempts = 0
        self.p2_attempts = 0
        self.last_activity = time.time()
        self.invite_msg_id: int | None = None
        self.board_msg_id: int | None = None

        self.last_guess_val: int | None = None
        self.last_guesser_name: str = ""
        self.last_hint_icon: str = ""


# Faol o'yinlar ro'yxati: game_id -> GameState
_active_games: Dict[str, GameState] = {}
# Foydalanuvchining faol o'yini: user_id -> game_id (bir vaqtda bir nechta juftlik o'ynashi uchun)
_user_games: Dict[int, str] = {}
# Chatdagi barcha faol o'yinlar to'plami: chat_id -> set[str] (game_ids)
_chat_games: Dict[int, set[str]] = {}


def cleanup_game(game_id: str):
    """O'yinni to'liq tozalash va o'yinchilarni ozod qilish."""
    game = _active_games.pop(game_id, None)
    if not game:
        return
    _user_games.pop(game.p1_id, None)
    if game.p2_id:
        _user_games.pop(game.p2_id, None)
    c_set = _chat_games.get(game.chat_id)
    if c_set:
        c_set.discard(game_id)
        if not c_set:
            _chat_games.pop(game.chat_id, None)


def cleanup_chat_game(chat_id: int):
    """Eski muvofiqlik uchun: chatdagi barcha o'yinlarni tozalash."""
    c_set = list(_chat_games.get(chat_id, set()))
    for gid in c_set:
        cleanup_game(gid)


def render_game_board(game: GameState) -> tuple[str, InlineKeyboardMarkup]:
    """Bitta jonli va chiroyli o'yin doskasi matnini va tugmalarini tayyorlash."""
    p1_tag = f"@{game.p1_username}" if game.p1_username else escape(game.p1_name)
    p2_tag = f"@{game.p2_username}" if game.p2_username else escape(game.p2_name)

    cur_name = game.p1_name if game.turn_user_id == game.p1_id else game.p2_name
    cur_tag = f"@{game.p1_username}" if game.turn_user_id == game.p1_id and game.p1_username else (
        f"@{game.p2_username}" if game.turn_user_id == game.p2_id and game.p2_username else escape(cur_name)
    )

    last_hint_str = ""
    if game.last_guess_val is not None:
        last_hint_str = (
            f"⚡️ <b>So‘nggi zarba:</b> <b>{escape(game.last_guesser_name)}</b> ➡️ "
            f"<code>{game.last_guess_val}</code> {game.last_hint_icon}\n"
        )

    text = (
        f"🎮 <b>«RAQAMNI TOP» DUELI #{game.game_id.upper()}</b>\n"
        f"⚔️ <b>{p1_tag}</b> <i>vs</i> <b>{p2_tag}</b>\n"
        f"🔢 <i>Oraliq: 1 dan {game.max_range} gacha</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{escape(game.p1_name)}</b> qidirmoqda: <code>[{game.p1_min} ... {game.p1_max}]</code>\n"
        f"👤 <b>{escape(game.p2_name)}</b> qidirmoqda: <code>[{game.p2_min} ... {game.p2_max}]</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{last_hint_str}"
        f"👉 <b>NAVBAT:</b> 🎯 <b>{cur_tag}</b>\n"
        f"✍️ <i>Raqib yashirgan raqamni topish uchun guruhga son yozing...</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛑 O‘yinni to‘xtatish", callback_data=f"g_stop:{game.game_id}")
        ]
    ])
    return text, kb


async def delete_message_later(bot: Bot, chat_id: int, message_id: int, delay: int = 7):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def auto_expire_invite(bot: Bot, chat_id: int, game_id: str, delay: int = 60):
    """60 soniya ichida qabul qilinmagan o'yin taklifini avtomatik bekor qilish."""
    await asyncio.sleep(delay)
    game = _active_games.get(game_id)
    if game and game.status == "invited":
        cleanup_game(game_id)
        try:
            if game.invite_msg_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=game.invite_msg_id,
                    text="⏱️ <b>«Raqamni Top» taklif vaqti tugadi!</b>\nRaqib 60 soniya ichida qabul qilmadi.",
                    parse_mode="HTML"
                )
        except Exception:
            pass


GAME_CMD_REGEX = re.compile(
    r"^(?:🎮\s*)?(?:/game(?:@\w+)?|game|/oyin(?:@\w+)?|oyin|/o['`’‘ʻ]?yin(?:@\w+)?|o['`’‘ʻ]?yin|/oyun(?:@\w+)?|oyun)(?:\s+.*)?$",
    re.IGNORECASE
)
STOP_CMD_REGEX = re.compile(
    r"^(?:🛑\s*)?(?:/stopgame(?:@\w+)?|stopgame|/oyintugat(?:@\w+)?|oyintugat|/stop(?:@\w+)?|stop)$",
    re.IGNORECASE
)
TOPGAME_CMD_REGEX = re.compile(
    r"^(?:🏆\s*)?(?:/topgame(?:@\w+)?|topgame|/gametop(?:@\w+)?|gametop|/topoyinchilar(?:@\w+)?|topoyinchilar)$",
    re.IGNORECASE
)
GAMESTATS_CMD_REGEX = re.compile(
    r"^(?:📊\s*)?(?:/gamestats(?:@\w+)?|gamestats|/mystats(?:@\w+)?|mystats|/statam(?:@\w+)?|statam)$",
    re.IGNORECASE
)
SETWINS_CMD_REGEX = re.compile(
    r"^(?:/setwins(?:@\w+)?|/setgamewins(?:@\w+)?|setwins|setgamewins)(?:\s+.*)?$",
    re.IGNORECASE
)


def is_game_related_message(message: types.Message) -> bool:
    """
    Faqatgina o'yinga tegishli xabarlarni filtrlash:
    1. Buyruqlar: /topgame, /gamestats, /stopgame, game @user, /game, /setwins
    2. Faol o'yindagi raqam taxminlari (faqat o'ynayotgan o'yinchilarning raqamli xabarlari)
    Bu filtr boshqa guruh xabarlari (moderatsiya, qoidalar, oddiy gaplar) to'xtab qolmasligi uchun shart!
    """
    text = (message.text or message.caption or "").strip()
    if not text:
        return False

    if (
        TOPGAME_CMD_REGEX.match(text)
        or GAMESTATS_CMD_REGEX.match(text)
        or STOP_CMD_REGEX.match(text)
        or SETWINS_CMD_REGEX.match(text)
        or GAME_CMD_REGEX.match(text)
    ):
        return True

    # Faqat ayni paytda faol o'yinda qatnashayotgan o'yinchilarning raqam xabarlarini ushlash
    if text.isdigit() and message.from_user:
        gid = _user_games.get(message.from_user.id)
        if gid:
            game = _active_games.get(gid)
            if game and game.chat_id == message.chat.id and game.status == "playing":
                return True

    return False



@router.message(
    F.chat.type == ChatType.PRIVATE,
    lambda msg: bool(GAME_CMD_REGEX.match((msg.text or msg.caption or "").strip()))
)
async def handle_game_in_private(message: types.Message, bot: Bot):
    """Foydalanuvchi botga shaxsiy xabarda /game yozganda guruhga qo'shishni taklif qilish."""
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Botni Guruhingizga Qo‘shish",
                url=f"https://t.me/{bot_username}?startgroup=game&admin=post_messages+delete_messages+restrict_members"
            )
        ]
    ])
    await message.reply(
        "🎮 <b>«Raqamni Top» o‘yini guruhlarda o‘ynaladi!</b>\n\n"
        "O‘yinni do‘stlaringiz bilan o‘ynash uchun botni guruhingizga qo‘shing va guruhda:\n"
        "👉 <code>game</code> yoki <code>game @do‘stingiz</code> deb yozing!\n\n"
        "🏆 <b>Sovg‘alar:</b> 30, 50 va 100 ta g‘alabaga erishganlarga 🎁 <b>25⭐, 50⭐ va 100⭐ Telegram Gift</b> sovg‘alari beriladi!",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    is_game_related_message
)
async def handle_game_messages(message: types.Message, bot: Bot):
    text = (message.text or message.caption or "").strip()
    if not text:
        return

    chat_id = message.chat.id
    now = time.time()

    # 1. TOP O'YINCHILAR REYTINGI: /topgame
    if TOPGAME_CMD_REGEX.match(text):
        top_list = get_top_game_players(chat_id, limit=10)
        if not top_list:
            await message.reply(
                "🏆 <b>«Raqamni Top» Reytingi</b>\n\n"
                "Guruhda hali hech kim o‘yinda g‘alaba qozonmagan.\n"
                "Birinchi bo‘lib o‘ynash uchun: <code>game @user</code>",
                parse_mode="HTML"
            )
            return

        lines = ["🏆 <b>«Raqamni Top» Eng Kuchli O‘yinchilari (TOP-10):</b>\n"]
        medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]

        for idx, p in enumerate(top_list):
            m_str = medals[idx] if idx < len(medals) else f"{idx+1}."
            name = escape(p["full_name"])
            uname = f" (@{p['username']})" if p.get("username") else ""
            wins = p["wins"]
            claimed = set(p.get("claimed_milestones", "").split(",")) if p.get("claimed_milestones") else set()

            badges = []
            if "30" in claimed:
                badges.append("🎁 25⭐")
            if "50" in claimed:
                badges.append("🚀 50⭐")
            if "100" in claimed:
                badges.append("🏆 100⭐")
            b_text = f" [{' | '.join(badges)}]" if badges else ""

            lines.append(f"{m_str} <b>{name}</b>{uname} — <b>{wins} ta g‘alaba</b>{b_text}")

        lines.append("\n🎁 <b>Telegram Gift Sovg‘alari:</b>")
        lines.append("• 30 ta g‘alaba ➡️ 🎁 <b>25 ⭐ Gift</b> (Quti)")
        lines.append("• 50 ta g‘alaba ➡️ 🚀 <b>50 ⭐ Gift</b> (Raketa)")
        lines.append("• 100 ta g‘alaba ➡️ 🏆 <b>100 ⭐ Gift</b> (Kubok)")
        lines.append("\n<i>O‘ynash uchun: <code>game @user</code></i>")

        await message.reply("\n".join(lines), parse_mode="HTML")
        return

    # 2. SHAXSIY STATISTIKA VA PROGRESS: /gamestats
    if GAMESTATS_CMD_REGEX.match(text):
        u = message.from_user
        stats = get_user_game_stats(chat_id, u.id)
        if not stats or stats.get("total_games", 0) == 0:
            await message.reply(
                "🎮 Siz hali «Raqamni Top» o‘yinini o‘ynamagansiz.\n"
                "O‘ynash uchun boshqa a’zoga reply qilib <code>game</code> deb yozing!",
                parse_mode="HTML"
            )
            return

        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        total = stats.get("total_games", 0)
        win_rate = int((wins / total) * 100) if total > 0 else 0
        claimed = set(stats.get("claimed_milestones", "").split(",")) if stats.get("claimed_milestones") else set()

        if wins >= 100:
            progress_text = "🎉 <b>Barcha sovg‘alar marrasiga (100+) erishilgan! 🏆</b>"
        elif wins >= 50:
            rem = 100 - wins
            pct = min(100, int((wins / 100) * 100))
            progress_text = f"Keyingi sovg‘a: 🏆 <b>100 ⭐ Gift</b> (yana {rem} ta g‘alaba)\nProgress: <b>{wins}/100</b> ({pct}%)"
        elif wins >= 30:
            rem = 50 - wins
            pct = min(100, int((wins / 50) * 100))
            progress_text = f"Keyingi sovg‘a: 🚀 <b>50 ⭐ Gift</b> (yana {rem} ta g‘alaba)\nProgress: <b>{wins}/50</b> ({pct}%)"
        else:
            rem = 30 - wins
            pct = min(100, int((wins / 30) * 100))
            progress_text = f"Keyingi sovg‘a: 🎁 <b>25 ⭐ Gift</b> (yana {rem} ta g‘alaba)\nProgress: <b>{wins}/30</b> ({pct}%)"

        badges = []
        if "30" in claimed:
            badges.append("🎁 25⭐ Gift")
        if "50" in claimed:
            badges.append("🚀 50⭐ Gift")
        if "100" in claimed:
            badges.append("🏆 100⭐ Gift")
        b_text = f"\n🎖️ <b>Yutilgan sovg‘alar:</b> {', '.join(badges)}" if badges else ""

        resp = (
            f"👤 <b>{escape(u.full_name)}</b> — O‘yin statistikasi:\n\n"
            f"🏆 G‘alabalar: <b>{wins} ta</b>\n"
            f"💀 Mag‘lubiyatlar: <b>{losses} ta</b>\n"
            f"🎲 Jami o‘yinlar: <b>{total} ta</b>\n"
            f"📊 G‘alaba ko‘rsatkichi: <b>{win_rate}%</b>{b_text}\n\n"
            f"🎁 <b>Sovg‘a holati:</b>\n{progress_text}"
        )
        await message.reply(resp, parse_mode="HTML")
        return
    now = time.time()

    # 1. Eski qotib qolgan o'yinlarni tozalash (3 daqiqa harakatsiz)
    stale_gids = [gid for gid, g in _active_games.items() if now - g.last_activity > 180]
    for gid in stale_gids:
        g = _active_games.get(gid)
        if g and g.board_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=g.chat_id,
                    message_id=g.board_msg_id,
                    text="⏱️ <b>«Raqamni Top» dueli vaqt tugashi sababli yakunlandi.</b> (3 daqiqa harakatsizlik)",
                    reply_markup=None,
                    parse_mode="HTML"
                )
            except Exception:
                pass
        cleanup_game(gid)

    # 2. O'YINNI TO'XTATISH: /stopgame
    if STOP_CMD_REGEX.match(text):
        u = message.from_user
        # A) Agar buyruq yuborgan foydalanuvchining o'zi biror faol duelda bo'lsa:
        if u.id in _user_games:
            gid = _user_games[u.id]
            game = _active_games.get(gid)
            if game:
                cleanup_game(gid)
                try:
                    if game.board_msg_id:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=game.board_msg_id,
                            text=f"🛑 <b>«Raqamni Top» dueli {escape(u.full_name)} tomonidan to‘xtatildi.</b>",
                            reply_markup=None,
                            parse_mode="HTML"
                        )
                except Exception:
                    pass
                smsg = await message.reply("🛑 <b>O‘yiningiz to‘xtatildi.</b>", parse_mode="HTML")
                asyncio.create_task(delete_message_later(bot, chat_id, smsg.message_id, delay=5))
                return

        # B) Agar guruh admini /stopgame deb yozsa:
        is_admin = False
        try:
            member = await bot.get_chat_member(chat_id, u.id)
            is_admin = member.status in ["administrator", "creator"]
        except Exception:
            pass

        if is_admin:
            chat_gids = list(_chat_games.get(chat_id, set()))
            if chat_gids:
                for gid in chat_gids:
                    g = _active_games.get(gid)
                    if g and g.board_msg_id:
                        try:
                            await bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=g.board_msg_id,
                                text="🛑 <b>Guruh admini tomonidan barcha o‘yinlar to‘xtatildi.</b>",
                                reply_markup=None,
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
                    cleanup_game(gid)
                smsg = await message.reply("🛑 <b>Admin tomonidan guruhdagi barcha o‘yinlar to‘xtatildi.</b>", parse_mode="HTML")
                asyncio.create_task(delete_message_later(bot, chat_id, smsg.message_id, delay=5))
                return
            else:
                smsg = await message.reply("ℹ️ Guruhda ayni paytda faol o‘yin yo‘q.")
                asyncio.create_task(delete_message_later(bot, chat_id, smsg.message_id, delay=5))
                return

        smsg = await message.reply("ℹ️ Siz ayni paytda hech qanday faol o‘yinda emassiz.")
        asyncio.create_task(delete_message_later(bot, chat_id, smsg.message_id, delay=5))
        return

    # 3. ADMIN: G'ALABALARNI O'RNATISH (/setwins @username 3)
    if SETWINS_CMD_REGEX.match(text):
        u = message.from_user
        is_owner = (
            u.id in BOT_OWNER_NOTIFY_IDS
            or (u.username and u.username.lower() in ("khojayev_ramz", "wdablyu"))
        )
        if not is_owner:
            await message.reply("⛔️ Bu buyruq faqat bot egasi uchun ruxsat etilgan!")
            return

        tokens = text.split()
        target_uid = None
        target_name = None
        target_uname = None
        wins_val = 0

        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user
            target_uid = target.id
            target_name = target.full_name
            target_uname = target.username
            if len(tokens) >= 2 and tokens[1].isdigit():
                wins_val = int(tokens[1])
        elif len(tokens) >= 3:
            arg = tokens[1]
            if tokens[2].isdigit():
                wins_val = int(tokens[2])
            if arg.startswith("@"):
                target_uname = arg.lstrip("@")
                udata = get_user_by_username(chat_id, target_uname)
                if udata:
                    target_uid = udata["user_id"]
                    target_name = udata["full_name"]
            elif arg.isdigit() and len(arg) >= 6:
                target_uid = int(arg)
                udata = get_user_by_id(target_uid)
                target_name = udata["full_name"] if udata else f"User {target_uid}"
                target_uname = udata.get("username") if udata else None

        if not target_uid and target_uname:
            try:
                gdata = group_db.get_user_id_by_username_global(target_uname)
                if gdata:
                    target_uid = gdata["user_id"]
                    target_name = gdata["full_name"]
            except Exception:
                pass

        if not target_uid:
            await message.reply(
                "ℹ️ <b>Sintaksis:</b>\n"
                "• Foydalanuvchiga reply qilib: <code>/setwins 3</code>\n"
                "• Yoki: <code>/setwins @username 3</code>",
                parse_mode="HTML"
            )
            return

        group_db.set_user_game_wins(
            chat_id=chat_id,
            user_id=target_uid,
            wins=wins_val,
            full_name=target_name,
            username=target_uname
        )

        name_display = f"@{target_uname}" if target_uname else escape(target_name or f"User {target_uid}")
        await message.reply(
            f"✅ <b>{name_display}</b> uchun «Raqamni Top» g‘alabalari soni <b>{wins_val} ta</b> qilib belgilandi!",
            parse_mode="HTML"
        )
        return

    # 4. YANGI O'YIN TAKLIFI: game @user yoki reply qilib "game" yoki shunchaki "game"
    if GAME_CMD_REGEX.match(text):
        tokens = text.split()
        if len(tokens) >= 2 and tokens[1].lower() in ("on", "off", "yoqish", "ochirish", "o'chirish", "o‘chirish"):
            is_admin = False
            try:
                member = await bot.get_chat_member(chat_id, message.from_user.id)
                is_admin = member.status in ("creator", "administrator")
            except Exception:
                pass
            if message.from_user and message.from_user.username and message.from_user.username.lower() in ("khojayev_ramz", "wdablyu"):
                is_admin = True
            if message.from_user and message.from_user.id in BOT_OWNER_NOTIFY_IDS:
                is_admin = True

            if not is_admin:
                await message.reply("⛔️ O‘yin tizimini yoqish yoki o‘chirish faqat guruh adminlari uchun ruxsat etilgan.")
                return

            enable = tokens[1].lower() in ("on", "yoqish")
            group_db.set_game_status(chat_id, enable)
            if enable:
                await message.reply(
                    "🎮 <b>Guruhda «Raqamni Top» o‘yin rejimi yoqildi!</b>\n"
                    "Endi a‘zolar <code>game</code> yoki <code>game @user</code> orqali duel o‘ynashi mumkin.",
                    parse_mode="HTML"
                )
            else:
                cleanup_chat_game(chat_id)
                await message.reply(
                    "🛑 <b>Guruhda «Raqamni Top» o‘yin rejimi o‘chirildi.</b>",
                    parse_mode="HTML"
                )
            return

        # Guruhda o'yin yoqilganmi tekshirish
        if not group_db.is_game_enabled(chat_id):
            msg = await message.reply(
                "ℹ️ <b>Ushbu guruhda «Raqamni Top» o‘yin rejimi o‘chirilgan.</b>\n"
                "Yoqish uchun guruh admini Mini App orqali yoki <code>/game on</code> deb yozishi kerak.",
                parse_mode="HTML"
            )
            asyncio.create_task(delete_message_later(bot, chat_id, msg.message_id, delay=60))
            return

        p1 = message.from_user
        if not p1:
            return

        # 1. Taklif qiluvchi (p1) allaqachon biror faol duelda qatnashayotgan bo'lsa:
        if p1.id in _user_games:
            existing_gid = _user_games[p1.id]
            existing_game = _active_games.get(existing_gid)
            if existing_game and existing_game.status != "finished":
                msg = await message.reply("⚠️ Siz ayni paytda faol duelda qatnashmoqdasiz! Avval uni yakunlang yoki /stopgame deb yozing.")
                asyncio.create_task(delete_message_later(bot, chat_id, msg.message_id, delay=8))
                return
            else:
                _user_games.pop(p1.id, None)

        p2_id = None
        p2_name = None
        p2_username = None

        # A) Reply qilinganmi?
        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user
            p2_id = target.id
            p2_name = target.full_name
            p2_username = target.username
        else:
            # B) Text mention entity bormi?
            entities = message.entities or message.caption_entities or []
            for ent in entities:
                if ent.type == "text_mention" and ent.user:
                    p2_id = ent.user.id
                    p2_name = ent.user.full_name
                    p2_username = ent.user.username
                    break

            # C) @username yoki ID ko'rsatilganmi?
            if not p2_id:
                tokens = text.split()
                if len(tokens) >= 2:
                    arg = tokens[1]
                    if arg.startswith("@"):
                        uname = arg.lstrip("@")
                        udata = get_user_by_username(chat_id, uname)
                        if udata:
                            p2_id = udata["user_id"]
                            p2_name = udata["full_name"]
                            p2_username = udata.get("username")
                        else:
                            try:
                                chat_admins = await bot.get_chat_administrators(chat_id)
                                for adm in chat_admins:
                                    if adm.user.username and adm.user.username.lower() == uname.lower():
                                        p2_id = adm.user.id
                                        p2_name = adm.user.full_name
                                        p2_username = adm.user.username
                                        break
                            except Exception:
                                pass
                            if not p2_id:
                                p2_name = f"@{uname}"
                                p2_username = uname
                    elif arg.isdigit() and len(arg) >= 6:
                        p2_id = int(arg)
                        udata = get_user_by_id(p2_id)
                        p2_name = udata["full_name"] if udata else f"O'yinchi [{p2_id}]"
                        p2_username = udata.get("username") if udata else None

        # 2. Taklif qilingan raqib (p2) allaqachon biror faol duelda bo'lsa:
        if p2_id and p2_id in _user_games:
            existing_gid = _user_games[p2_id]
            existing_game = _active_games.get(existing_gid)
            if existing_game and existing_game.status != "finished":
                msg = await message.reply(
                    f"⚠️ <b>{escape(p2_name or 'Foydalanuvchi')}</b> ayni paytda boshqa duelda qatnashmoqda! "
                    f"Kuting yoki boshqa raqibni chorlang.",
                    parse_mode="HTML"
                )
                asyncio.create_task(delete_message_later(bot, chat_id, msg.message_id, delay=8))
                return
            else:
                _user_games.pop(p2_id, None)

        is_open_challenge = not p2_id and not p2_username

        if not is_open_challenge:
            bot_info = await bot.get_me()
            if p2_id == bot_info.id:
                await message.reply("🤖 Bot bilan o‘ynab bo‘lmaydi! Tirik insonni o‘yinga chorlang 😊")
                return

            if p2_id == p1.id:
                await message.reply("😂 O‘zingiz bilan o‘zingiz o‘ynay olmaysiz! Boshqa do‘stingizni chorlang.")
                return

        game_id = uuid.uuid4().hex[:8]
        new_game = GameState(
            game_id=game_id,
            chat_id=chat_id,
            p1_id=p1.id,
            p1_name=p1.full_name,
            p1_username=p1.username,
            p2_id=p2_id or 0,
            p2_name=p2_name or "Ixtiyoriy a'zo",
            p2_username=p2_username
        )

        _active_games[game_id] = new_game
        _user_games[p1.id] = game_id
        if p2_id:
            _user_games[p2_id] = game_id
        if chat_id not in _chat_games:
            _chat_games[chat_id] = set()
        _chat_games[chat_id].add(game_id)

        p1_tag = f"@{p1.username}" if p1.username else escape(p1.full_name)

        if is_open_challenge:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚔️ Jangga qo‘shilish", callback_data=f"g_acc:{game_id}"),
                    InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"g_dec:{game_id}")
                ]
            ])
            invite_text = (
                f"🎮 <b>«Raqamni Top» Ochiq Jangi!</b>\n\n"
                f"👤 <b>{p1_tag}</b> guruhdagi barcha a‘zolarni raqam topish dueliga chorladi!\n\n"
                f"<i>Raqib yashirgan sirli raqamni birinchi bo‘lib kim topadi?</i>\n"
                f"🎯 <i>Duelga kirishish uchun pastdagi «⚔️ Jangga qo‘shilish» tugmasini bosing (60 soniya)...</i>"
            )
        else:
            p2_tag = f"@{p2_username}" if p2_username else escape(p2_name or "Raqib")
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"g_acc:{game_id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"g_dec:{game_id}")
                ]
            ])
            invite_text = (
                f"🎮 <b>«Raqamni Top» Jangi!</b>\n\n"
                f"👤 <b>{p1_tag}</b> sizni raqam topish dueliga chorladi, <b>{p2_tag}</b>!\n\n"
                f"<i>Raqib yashirgan sirli raqamni birinchi bo‘lib kim topadi?</i>\n"
                f"⏱️ <i>Qabul qilish uchun 60 soniya...</i>"
            )

        invite_msg = await message.answer(
            invite_text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        new_game.invite_msg_id = invite_msg.message_id
        asyncio.create_task(auto_expire_invite(bot, chat_id, game_id, delay=60))
        return

    # 4. O'YIN JARAYONIDAGI RAQAM TAXMINLARI:
    u = message.from_user
    if u and u.id in _user_games:
        gid = _user_games[u.id]
        game = _active_games.get(gid)
        if game and game.status == "playing" and game.chat_id == chat_id:
            clean_num = text.strip()
            if clean_num.isdigit():
                guess_val = int(clean_num)

                # Guruhni xabarlar bilan to'ldirmaslik uchun o'yinchining raqam xabarini DARHOL o'chiramiz!
                try:
                    await message.delete()
                    from group_bot.database import delete_message_record
                    delete_message_record(chat_id, message.message_id)
                except Exception:
                    pass

                # Hozirgi navbat kimda?
                if u.id != game.turn_user_id:
                    cur_name = game.p1_name if game.turn_user_id == game.p1_id else game.p2_name
                    wmsg = await message.answer(
                        f"⏳ <b>{escape(u.full_name)}</b>, hozir sizning navbatingiz emas! <b>{escape(cur_name)}</b> taxmin qilmoqda.",
                        parse_mode="HTML"
                    )
                    asyncio.create_task(delete_message_later(bot, chat_id, wmsg.message_id, delay=3))
                    return

                # Diapazondan chiqib ketgan bo'lsa
                if guess_val < 1 or guess_val > game.max_range:
                    wmsg = await message.answer(
                        f"⚠️ <b>{escape(u.full_name)}</b>, raqam <b>1</b> va <b>{game.max_range}</b> oralig‘ida bo‘lishi kerak!",
                        parse_mode="HTML"
                    )
                    asyncio.create_task(delete_message_later(bot, chat_id, wmsg.message_id, delay=3))
                    return

                game.last_activity = time.time()
                game.last_guess_val = guess_val
                game.last_guesser_name = u.full_name

                # A) P1 taxmin qildi (P2 ning raqamini qidirmoqda):
                if u.id == game.p1_id:
                    game.p1_attempts += 1
                    target_secret = game.p2_secret

                    # G'ALABA!
                    if guess_val == target_secret:
                        game.status = "finished"
                        cleanup_game(game.game_id)

                        winner_wins, new_milestones = record_game_result(
                            chat_id=chat_id,
                            winner_id=game.p1_id,
                            winner_name=game.p1_name,
                            winner_uname=game.p1_username,
                            loser_id=game.p2_id,
                            loser_name=game.p2_name,
                            loser_uname=game.p2_username
                        )

                        win_text = (
                            f"🏆 <b>BINGO! G‘ALABA!</b> 🎉🎉🎉\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👑 <b>{escape(game.p1_name)}</b> raqib <b>{escape(game.p2_name)}</b> yashirgan "
                            f"<b>{guess_val}</b> raqamini <b>{game.p1_attempts} ta urinishda</b> topdi va mutlaq g‘olib bo‘ldi! 🥇\n\n"
                            f"📊 <b>{escape(game.p1_name)}</b> jami g‘alabalari: <b>{winner_wins} ta</b>\n"
                            f"🤫 <b>{escape(game.p1_name)}</b>ning o‘z maxfiy raqami: <b>{game.p1_secret}</b> edi.\n\n"
                            f"👏 <i>Ajoyib intellektual jang bo‘ldi!</i>"
                        )
                        win_kb = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="🎮 Yangi o‘yin", callback_data="g_new_quick"),
                                InlineKeyboardButton(text="🏆 Top o‘yinchilar", callback_data="g_show_top")
                            ]
                        ])

                        try:
                            if game.board_msg_id:
                                await bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=game.board_msg_id,
                                    text=win_text,
                                    reply_markup=win_kb,
                                    parse_mode="HTML"
                                )
                            else:
                                await message.answer(win_text, reply_markup=win_kb, parse_mode="HTML")
                        except Exception:
                            await message.answer(win_text, reply_markup=win_kb, parse_mode="HTML")

                        # Agar yangi sovg'a marrasiga yetgan bo'lsa (30, 50, 100)
                        for m in new_milestones:
                            gift = GIFT_MILESTONES.get(m)
                            if gift:
                                await message.answer(
                                    f"🎁⭐ <b>DIQQAT! KATTA SOVG‘A YUTIB OLINDI!</b> ⭐🎁\n\n"
                                    f"🎉 <b>{escape(game.p1_name)}</b> «Raqamni Top» o‘yinida <b>{m} ta g‘alaba</b> marrasiga yetdi va "
                                    f"<b>{gift['icon']} {gift['stars']} ⭐ {gift['name']}</b> sovg‘asini yutib oldi! 🥳\n\n"
                                    f"<i>G‘olibga sovg‘asi tez orada yuboriladi yoki @khojayev_ramz bilan bog‘laning!</i>",
                                    parse_mode="HTML"
                                )
                                chat_title = message.chat.title or "Guruh"
                                w_uname_str = f"@{game.p1_username}" if game.p1_username else "usernamesiz"
                                admin_text = (
                                    f"🚨 <b>YANGI TELEGRAM GIFT G‘OLIBI!</b> 🎁⭐\n\n"
                                    f"👤 <b>G‘olib:</b> {escape(game.p1_name)} ({w_uname_str}) [ID: <code>{game.p1_id}</code>]\n"
                                    f"💬 <b>Guruh:</b> {escape(chat_title)} [ID: <code>{chat_id}</code>]\n"
                                    f"🏆 <b>G‘alabalar soni:</b> {winner_wins} ta\n"
                                    f"🎁 <b>Yutuq:</b> {gift['icon']} <b>{gift['stars']} ⭐ {gift['name']}</b> ({m} ta g‘alaba marrasi)\n\n"
                                    f"🔗 <a href='tg://user?id={game.p1_id}'>Foydalanuvchi profiliga o‘tish</a>"
                                )
                                for admin_id in BOT_OWNER_NOTIFY_IDS:
                                    try:
                                        await bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="HTML")
                                    except Exception:
                                        pass
                        return

                    # Topolmadi: Tepa yoki Past
                    if guess_val < target_secret:
                        game.p1_min = max(game.p1_min, guess_val + 1)
                        game.last_hint_icon = "🔼 <b>TEPA (Kattaroq!)</b>"
                    else:
                        game.p1_max = min(game.p1_max, guess_val - 1)
                        game.last_hint_icon = "🔽 <b>PAST (Kichikroq!)</b>"

                    # Navbat P2 ga o'tadi
                    game.turn_user_id = game.p2_id

                    board_text, board_kb = render_game_board(game)
                    try:
                        if game.board_msg_id:
                            await bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=game.board_msg_id,
                                text=board_text,
                                reply_markup=board_kb,
                                parse_mode="HTML"
                            )
                        else:
                            bmsg = await message.answer(board_text, reply_markup=board_kb, parse_mode="HTML")
                            game.board_msg_id = bmsg.message_id
                    except TelegramBadRequest as e:
                        if "message is not modified" not in str(e).lower():
                            bmsg = await message.answer(board_text, reply_markup=board_kb, parse_mode="HTML")
                            game.board_msg_id = bmsg.message_id
                    except Exception:
                        pass
                    return

                # B) P2 taxmin qildi (P1 ning raqamini qidirmoqda):
                elif u.id == game.p2_id:
                    game.p2_attempts += 1
                    target_secret = game.p1_secret

                    # G'ALABA!
                    if guess_val == target_secret:
                        game.status = "finished"
                        cleanup_game(game.game_id)

                        winner_wins, new_milestones = record_game_result(
                            chat_id=chat_id,
                            winner_id=game.p2_id,
                            winner_name=game.p2_name,
                            winner_uname=game.p2_username,
                            loser_id=game.p1_id,
                            loser_name=game.p1_name,
                            loser_uname=game.p1_username
                        )

                        win_text = (
                            f"🏆 <b>BINGO! G‘ALABA!</b> 🎉🎉🎉\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"👑 <b>{escape(game.p2_name)}</b> raqib <b>{escape(game.p1_name)}</b> yashirgan "
                            f"<b>{guess_val}</b> raqamini <b>{game.p2_attempts} ta urinishda</b> topdi va mutlaq g‘olib bo‘ldi! 🥇\n\n"
                            f"📊 <b>{escape(game.p2_name)}</b> jami g‘alabalari: <b>{winner_wins} ta</b>\n"
                            f"🤫 <b>{escape(game.p2_name)}</b>ning o‘z maxfiy raqami: <b>{game.p2_secret}</b> edi.\n\n"
                            f"👏 <i>Ajoyib intellektual jang bo‘ldi!</i>"
                        )
                        win_kb = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="🎮 Yangi o‘yin", callback_data="g_new_quick"),
                                InlineKeyboardButton(text="🏆 Top o‘yinchilar", callback_data="g_show_top")
                            ]
                        ])

                        try:
                            if game.board_msg_id:
                                await bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=game.board_msg_id,
                                    text=win_text,
                                    reply_markup=win_kb,
                                    parse_mode="HTML"
                                )
                            else:
                                await message.answer(win_text, reply_markup=win_kb, parse_mode="HTML")
                        except Exception:
                            await message.answer(win_text, reply_markup=win_kb, parse_mode="HTML")

                        # Agar yangi sovg'a marrasiga yetgan bo'lsa (30, 50, 100)
                        for m in new_milestones:
                            gift = GIFT_MILESTONES.get(m)
                            if gift:
                                await message.answer(
                                    f"🎁⭐ <b>DIQQAT! KATTA SOVG‘A YUTIB OLINDI!</b> ⭐🎁\n\n"
                                    f"🎉 <b>{escape(game.p2_name)}</b> «Raqamni Top» o‘yinida <b>{m} ta g‘alaba</b> marrasiga yetdi va "
                                    f"<b>{gift['icon']} {gift['stars']} ⭐ {gift['name']}</b> sovg‘asini yutib oldi! 🥳\n\n"
                                    f"<i>G‘olibga sovg‘asi tez orada yuboriladi yoki @khojayev_ramz bilan bog‘laning!</i>",
                                    parse_mode="HTML"
                                )
                                chat_title = message.chat.title or "Guruh"
                                w_uname_str = f"@{game.p2_username}" if game.p2_username else "usernamesiz"
                                admin_text = (
                                    f"🚨 <b>YANGI TELEGRAM GIFT G‘OLIBI!</b> 🎁⭐\n\n"
                                    f"👤 <b>G‘olib:</b> {escape(game.p2_name)} ({w_uname_str}) [ID: <code>{game.p2_id}</code>]\n"
                                    f"💬 <b>Guruh:</b> {escape(chat_title)} [ID: <code>{chat_id}</code>]\n"
                                    f"🏆 <b>G‘alabalar soni:</b> {winner_wins} ta\n"
                                    f"🎁 <b>Yutuq:</b> {gift['icon']} <b>{gift['stars']} ⭐ {gift['name']}</b> ({m} ta g‘alaba marrasi)\n\n"
                                    f"🔗 <a href='tg://user?id={game.p2_id}'>Foydalanuvchi profiliga o‘tish</a>"
                                )
                                for admin_id in BOT_OWNER_NOTIFY_IDS:
                                    try:
                                        await bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="HTML")
                                    except Exception:
                                        pass
                        return

                    # Topolmadi: Tepa yoki Past
                    if guess_val < target_secret:
                        game.p2_min = max(game.p2_min, guess_val + 1)
                        game.last_hint_icon = "🔼 <b>TEPA (Kattaroq!)</b>"
                    else:
                        game.p2_max = min(game.p2_max, guess_val - 1)
                        game.last_hint_icon = "🔽 <b>PAST (Kichikroq!)</b>"

                    # Navbat P1 ga o'tadi
                    game.turn_user_id = game.p1_id

                    board_text, board_kb = render_game_board(game)
                    try:
                        if game.board_msg_id:
                            await bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=game.board_msg_id,
                                text=board_text,
                                reply_markup=board_kb,
                                parse_mode="HTML"
                            )
                        else:
                            bmsg = await message.answer(board_text, reply_markup=board_kb, parse_mode="HTML")
                            game.board_msg_id = bmsg.message_id
                    except TelegramBadRequest as e:
                        if "message is not modified" not in str(e).lower():
                            bmsg = await message.answer(board_text, reply_markup=board_kb, parse_mode="HTML")
                            game.board_msg_id = bmsg.message_id
                    except Exception:
                        pass
                    return


# -------------------------------------------------------------
# CALLBACK QUERY HANDLERS (Tugmalar bosilganda)
# -------------------------------------------------------------

@router.callback_query(F.data.startswith("g_acc:"))
async def on_game_accept(query: CallbackQuery, bot: Bot):
    game_id = query.data.split(":")[1]
    game = _active_games.get(game_id)
    if not game:
        await query.answer("Bu o‘yin allaqachon tugagan yoki bekor qilingan.", show_alert=True)
        return

    if not group_db.is_game_enabled(game.chat_id):
        await query.answer("🛑 Bu guruhda o‘yin rejimi o‘chirilgan!", show_alert=True)
        return

    u = query.from_user

    # O'ziga o'zi qarshi o'ynashni oldini olish
    if u.id == game.p1_id:
        await query.answer("😂 O‘zingizga qarshi o‘ynay olmaysiz! Guruhdagi boshqa a‘zo qabul qilishi kerak.", show_alert=True)
        return

    # Faqat taklif qilingan P2 qabul qila oladi (agar P2_id 0 bo'lsa, username tekshiriladi)
    if game.p2_id and game.p2_id != u.id:
        await query.answer("❌ Bu taklif sizga emas!", show_alert=True)
        return
    elif not game.p2_id and game.p2_username:
        if not u.username or u.username.lower() != game.p2_username.lower():
            await query.answer("❌ Bu taklif sizga emas!", show_alert=True)
            return

    # Qabul qilayotgan foydalanuvchi allaqachon boshqa duelda emasmi?
    if u.id in _user_games:
        existing_gid = _user_games[u.id]
        if existing_gid != game_id:
            existing_game = _active_games.get(existing_gid)
            if existing_game and existing_game.status != "finished":
                await query.answer("⚠️ Siz ayni paytda boshqa faol duelda qatnashmoqdasiz!", show_alert=True)
                return
            else:
                _user_games.pop(u.id, None)

    # P2 ma'lumotlarini aniqlashtirish
    game.p2_id = u.id
    game.p2_name = u.full_name
    game.p2_username = u.username
    _user_games[u.id] = game_id
    game.status = "range_select"
    game.last_activity = time.time()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔢 1 — 100", callback_data=f"g_rng:{game_id}:100"),
            InlineKeyboardButton(text="🔢 1 — 1000", callback_data=f"g_rng:{game_id}:1000")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"g_dec:{game_id}")
        ]
    ])

    try:
        await query.message.edit_text(
            f"🎯 <b>Jang taklifi qabul qilindi!</b>\n\n"
            f"👤 <b>{escape(game.p1_name)}</b> ⚔️ <b>{escape(game.p2_name)}</b>\n\n"
            f"Quyidan o‘yin oralig‘ini tanlang:",
            reply_markup=kb,
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass
    await query.answer()


@router.callback_query(F.data.startswith("g_dec:"))
async def on_game_decline(query: CallbackQuery):
    game_id = query.data.split(":")[1]
    game = _active_games.get(game_id)
    if not game:
        await query.answer("O‘yin allaqachon yakunlangan.")
        return

    u = query.from_user
    if u.id not in (game.p1_id, game.p2_id):
        await query.answer("❌ Siz bu o‘yinda qatnashmaysiz!", show_alert=True)
        return

    cleanup_game(game_id)
    await query.message.edit_text(f"❌ <b>{escape(u.full_name)}</b> tomonidan o‘yin bekor qilindi.", parse_mode="HTML")
    await query.answer()


@router.callback_query(F.data.startswith("g_rng:"))
async def on_range_select(query: CallbackQuery):
    parts = query.data.split(":")
    game_id = parts[1]
    range_val = int(parts[2])

    game = _active_games.get(game_id)
    if not game:
        await query.answer("O‘yin topilmadi.")
        return

    u = query.from_user
    if u.id not in (game.p1_id, game.p2_id):
        await query.answer("❌ Siz bu o‘yinda qatnashmaysiz!", show_alert=True)
        return

    game.max_range = range_val
    game.p1_min = 1
    game.p1_max = range_val
    game.p2_min = 1
    game.p2_max = range_val
    game.status = "picking"
    game.last_activity = time.time()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 Maxfiy raqamimni olish", callback_data=f"g_pick:{game_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"g_dec:{game_id}")
        ]
    ])

    await query.message.edit_text(
        f"🔢 <b>Oraliq tanlandi: 1 dan {range_val} gacha!</b>\n\n"
        f"Har ikkala o‘yinchi pastdagi <b>«🎲 Maxfiy raqamimni olish»</b> tugmasini bosishi kerak.\n"
        f"Bot sizga sirli raqam beradi va uni faqat o‘zingiz ekranda ko‘rasiz (hech kim bilmaydi)!\n\n"
        f"👤 {escape(game.p1_name)}: ⏳ <i>Kutilmoqda...</i>\n"
        f"👤 {escape(game.p2_name)}: ⏳ <i>Kutilmoqda...</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await query.answer()


@router.callback_query(F.data.startswith("g_pick:"))
async def on_secret_pick(query: CallbackQuery, bot: Bot):
    game_id = query.data.split(":")[1]
    game = _active_games.get(game_id)
    if not game:
        await query.answer("O‘yin topilmadi.")
        return

    u = query.from_user
    if u.id not in (game.p1_id, game.p2_id):
        await query.answer("❌ Siz bu o‘yinda qatnashmaysiz!", show_alert=True)
        return

    # Raqam tanlash
    if u.id == game.p1_id:
        if game.p1_secret is None:
            game.p1_secret = random.randint(1, game.max_range)
        secret_num = game.p1_secret
    else:
        if game.p2_secret is None:
            game.p2_secret = random.randint(1, game.max_range)
        secret_num = game.p2_secret

    game.last_activity = time.time()

    # O'yinchining o'ziga popup alert bilan ko'rsatamiz (guruhdagilar ko'rmaydi!)
    await query.answer(
        f"🤫 Sizning MAXFIY raqamingiz: {secret_num}!\n"
        f"Uni hech kimga aytmang. Raqibingiz shuni topishi kerak!",
        show_alert=True
    )

    p1_status = "✅ <b>Tayyor!</b>" if game.p1_secret else "⏳ <i>Kutilmoqda...</i>"
    p2_status = "✅ <b>Tayyor!</b>" if game.p2_secret else "⏳ <i>Kutilmoqda...</i>"

    # Ikkala o'yinchi ham raqam olib bo'ldimi?
    if game.p1_secret and game.p2_secret:
        game.status = "playing"
        game.turn_user_id = game.p1_id  # 1-o'yinchi boshlaydi
        game.board_msg_id = query.message.message_id

        board_text, board_kb = render_game_board(game)
        try:
            await query.message.edit_text(
                board_text,
                reply_markup=board_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎲 Maxfiy raqamimni olish", callback_data=f"g_pick:{game_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"g_dec:{game_id}")
            ]
        ])
        try:
            await query.message.edit_text(
                f"🔢 <b>Oraliq tanlandi: 1 dan {game.max_range} gacha!</b>\n\n"
                f"Pastdagi tugmani bosib maxfiy raqamingizni oling:\n\n"
                f"👤 {escape(game.p1_name)}: {p1_status}\n"
                f"👤 {escape(game.p2_name)}: {p2_status}",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("g_stop:"))
async def on_game_stop_button(query: CallbackQuery, bot: Bot):
    game_id = query.data.split(":")[1]
    game = _active_games.get(game_id)
    if not game:
        await query.answer("O‘yin allaqachon yakunlangan.")
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    u = query.from_user
    is_player = u.id in (game.p1_id, game.p2_id)
    is_admin = False
    try:
        member = await bot.get_chat_member(game.chat_id, u.id)
        is_admin = member.status in ["administrator", "creator"]
    except Exception:
        pass

    if not is_player and not is_admin:
        await query.answer("❌ O‘yinni faqat uning o‘yinchilari yoki guruh admini to‘xtata oladi!", show_alert=True)
        return

    cleanup_game(game_id)
    stop_text = f"🛑 <b>«Raqamni Top» dueli {escape(u.full_name)} tomonidan to‘xtatildi.</b>"
    try:
        await query.message.edit_text(stop_text, reply_markup=None, parse_mode="HTML")
    except Exception:
        pass
    await query.answer("O‘yin to‘xtatildi.")


@router.callback_query(F.data == "g_new_quick")
async def on_game_new_quick(query: CallbackQuery):
    await query.answer("🎮 Yangi duel boshlash uchun guruhga: game @do‘stingiz deb yozing!", show_alert=True)


@router.callback_query(F.data == "g_show_top")
async def on_game_show_top(query: CallbackQuery):
    top_list = get_top_game_players(query.message.chat.id, limit=5)
    if not top_list:
        await query.answer("🏆 Guruhda hali hech kim o‘yinda g‘alaba qozonmagan.", show_alert=True)
        return
    medals = ["🥇", "🥈", "🥉", "4.", "5."]
    lines = ["🏆 TOP-5 Kuchli O‘yinchilar:"]
    for idx, p in enumerate(top_list[:5]):
        lines.append(f"{medals[idx]} {p['full_name']} — {p['wins']} ta g‘alaba")
    await query.answer("\n".join(lines), show_alert=True)

