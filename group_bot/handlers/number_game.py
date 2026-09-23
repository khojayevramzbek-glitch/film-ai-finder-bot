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
    from group_bot.database import (
        get_user_by_username, get_user_by_id,
        record_game_result, get_user_game_stats, get_top_game_players
    )
except ImportError:
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


# Faol o'yinlar ro'yxati: game_id -> GameState
_active_games: Dict[str, GameState] = {}
# Chatdagi faol o'yin: chat_id -> game_id
_chat_games: Dict[int, str] = {}


def cleanup_chat_game(chat_id: int):
    gid = _chat_games.pop(chat_id, None)
    if gid:
        _active_games.pop(gid, None)


async def delete_message_later(bot: Bot, chat_id: int, message_id: int, delay: int = 7):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


GAME_CMD_REGEX = re.compile(r"^(?:/game|game)\b", re.IGNORECASE)
STOP_CMD_REGEX = re.compile(r"^(?:/stopgame|stopgame|/oyintugat|oyintugat)\b", re.IGNORECASE)
TOPGAME_CMD_REGEX = re.compile(r"^(?:/topgame|topgame|/gametop|gametop)\b", re.IGNORECASE)
GAMESTATS_CMD_REGEX = re.compile(r"^(?:/gamestats|gamestats|/mystats|mystats)\b", re.IGNORECASE)


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
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

    # 1. Eski qotib qolgan o'yinlarni tozalash (5 daqiqa harakatsiz)
    if chat_id in _chat_games:
        current_gid = _chat_games[chat_id]
        game_obj = _active_games.get(current_gid)
        if game_obj and now - game_obj.last_activity > 300:
            cleanup_chat_game(chat_id)

    # 2. O'YINNI TO'XTATISH: /stopgame
    if STOP_CMD_REGEX.match(text):
        if chat_id in _chat_games:
            gid = _chat_games[chat_id]
            game = _active_games.get(gid)
            if game:
                # O'yinchilar yoki admin to'xtata oladi
                if message.from_user.id in (game.p1_id, game.p2_id):
                    cleanup_chat_game(chat_id)
                    await message.reply("🛑 <b>«Raqamni Top» o‘yini to‘xtatildi.</b>", parse_mode="HTML")
                    return
                # Agar boshqa a'zo bo'lsa
                member = await bot.get_chat_member(chat_id, message.from_user.id)
                if member.status in ["administrator", "creator"]:
                    cleanup_chat_game(chat_id)
                    await message.reply("🛑 <b>Admin tomonidan o‘yin to‘xtatildi.</b>", parse_mode="HTML")
                    return
        return

    # 3. YANGI O'YIN TAKLIFI: game @user yoki reply qilib "game"
    if GAME_CMD_REGEX.match(text):
        # Guruhda ayni paytda faol o'yin bormi?
        if chat_id in _chat_games:
            gid = _chat_games[chat_id]
            existing_game = _active_games.get(gid)
            if existing_game and existing_game.status in ["invited", "range_select", "picking", "playing"]:
                msg = await message.reply("⚠️ Guruhda ayni paytda faol o‘yin ketmoqda! Avval uni yakunlang yoki /stopgame deb yozing.")
                asyncio.create_task(delete_message_later(bot, chat_id, msg.message_id, delay=10))
                return

        p1 = message.from_user
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
                            p2_name = f"@{uname}"
                            p2_username = uname
                    elif arg.isdigit() and len(arg) >= 6:
                        p2_id = int(arg)
                        udata = get_user_by_id(p2_id)
                        p2_name = udata["full_name"] if udata else f"O'yinchi [{p2_id}]"
                        p2_username = udata.get("username") if udata else None

        if not p2_id and not p2_username:
            msg = await message.reply(
                "🎮 <b>Kim bilan o‘ynamoqchisiz?</b>\n"
                "Foydalanuvchining xabariga reply qilib <code>game</code> deb yozing yoki:\n"
                "👉 <code>game @username</code> shaklida yuboring.",
                parse_mode="HTML"
            )
            asyncio.create_task(delete_message_later(bot, chat_id, msg.message_id, delay=15))
            return

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
            p2_name=p2_name or "Raqib",
            p2_username=p2_username
        )

        _active_games[game_id] = new_game
        _chat_games[chat_id] = game_id

        p1_tag = f"@{p1.username}" if p1.username else escape(p1.full_name)
        p2_tag = f"@{p2_username}" if p2_username else escape(p2_name or "Raqib")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"g_acc:{game_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"g_dec:{game_id}")
            ]
        ])

        invite_msg = await message.answer(
            f"🎮 <b>«Raqamni Top» Jangi!</b>\n\n"
            f"👤 <b>{p1_tag}</b> sizni raqam topish dueliga chorladi, <b>{p2_tag}</b>!\n\n"
            f"<i>Raqib yashirgan sirli raqamni birinchi bo‘lib kim topadi?</i>\n"
            f"⏱️ <i>Qabul qilish uchun 60 soniya...</i>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        new_game.invite_msg_id = invite_msg.message_id
        return

    # 4. O'YIN JARAYONIDAGI RAQAM TAXMINLARI:
    if chat_id in _chat_games:
        gid = _chat_games[chat_id]
        game = _active_games.get(gid)
        if game and game.status == "playing":
            # Faqat raqam yozilgan bo'lsa
            clean_num = text.strip()
            if clean_num.isdigit():
                guess_val = int(clean_num)
                u = message.from_user

                # Hozirgi navbat kimda?
                if u.id != game.turn_user_id:
                    # Agar navbati bo'lmagan 2-o'yinchi raqam yozsa
                    if u.id in (game.p1_id, game.p2_id):
                        cur_name = game.p1_name if game.turn_user_id == game.p1_id else game.p2_name
                        wmsg = await message.reply(f"⏳ Hozir sizning navbatingiz emas! <b>{escape(cur_name)}</b> taxmin qilmoqda.", parse_mode="HTML")
                        asyncio.create_task(delete_message_later(bot, chat_id, wmsg.message_id, delay=5))
                    return

                # Diapazondan chiqib ketgan bo'lsa
                if guess_val < 1 or guess_val > game.max_range:
                    wmsg = await message.reply(f"⚠️ Raqam <b>1</b> va <b>{game.max_range}</b> oralig‘ida bo‘lishi kerak!", parse_mode="HTML")
                    asyncio.create_task(delete_message_later(bot, chat_id, wmsg.message_id, delay=5))
                    return

                game.last_activity = time.time()

                # A) P1 taxmin qildi (P2 ning raqamini qidirmoqda):
                if u.id == game.p1_id:
                    game.p1_attempts += 1
                    target_secret = game.p2_secret

                    # G'ALABA!
                    if guess_val == target_secret:
                        game.status = "finished"
                        cleanup_chat_game(chat_id)

                        winner_wins, new_milestones = record_game_result(
                            chat_id=chat_id,
                            winner_id=game.p1_id,
                            winner_name=game.p1_name,
                            winner_uname=game.p1_username,
                            loser_id=game.p2_id,
                            loser_name=game.p2_name,
                            loser_uname=game.p2_username
                        )

                        await message.answer(
                            f"🏆 <b>BINGO! G‘ALABA!</b> 🎉🎉🎉\n\n"
                            f"👑 <b>{escape(game.p1_name)}</b> raqib <b>{escape(game.p2_name)}</b> yashirgan <b>{guess_val}</b> raqamini <b>{game.p1_attempts} ta urinishda</b> topdi va mutlaq g‘olib bo‘ldi! 🥇\n"
                            f"📊 Jami g‘alabalari: <b>{winner_wins} ta</b>\n"
                            f"<i>{escape(game.p1_name)}ning o‘z raqami esa: {game.p1_secret} edi.</i>\n"
                            f"Ajoyib intellektual jang bo‘ldi! 👏",
                            parse_mode="HTML"
                        )

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
                        hint_icon = "🔼 <b>TEPA (Kattaroq!)</b>"
                    else:
                        game.p1_max = min(game.p1_max, guess_val - 1)
                        hint_icon = "🔽 <b>PAST (Kichikroq!)</b>"

                    # Navbat P2 ga o'tadi
                    game.turn_user_id = game.p2_id
                    next_player_name = game.p2_name
                    target_player_name = game.p1_name

                    await message.answer(
                        f"👤 <b>{escape(game.p1_name)}</b>: <code>{guess_val}</code> ➡️ {hint_icon}\n"
                        f"📊 {escape(game.p1_name)} uchun oraliq: <code>[{game.p1_min} ... {game.p1_max}]</code>\n\n"
                        f"🎯 <b>Navbat:</b> <b>{escape(next_player_name)}</b>!\n"
                        f"<i>{escape(target_player_name)} yashirgan raqamni topish uchun raqam yozing:</i>",
                        parse_mode="HTML"
                    )
                    return

                # B) P2 taxmin qildi (P1 ning raqamini qidirmoqda):
                elif u.id == game.p2_id:
                    game.p2_attempts += 1
                    target_secret = game.p1_secret

                    # G'ALABA!
                    if guess_val == target_secret:
                        game.status = "finished"
                        cleanup_chat_game(chat_id)

                        winner_wins, new_milestones = record_game_result(
                            chat_id=chat_id,
                            winner_id=game.p2_id,
                            winner_name=game.p2_name,
                            winner_uname=game.p2_username,
                            loser_id=game.p1_id,
                            loser_name=game.p1_name,
                            loser_uname=game.p1_username
                        )

                        await message.answer(
                            f"🏆 <b>BINGO! G‘ALABA!</b> 🎉🎉🎉\n\n"
                            f"👑 <b>{escape(game.p2_name)}</b> raqib <b>{escape(game.p1_name)}</b> yashirgan <b>{guess_val}</b> raqamini <b>{game.p2_attempts} ta urinishda</b> topdi va mutlaq g‘olib bo‘ldi! 🥇\n"
                            f"📊 Jami g‘alabalari: <b>{winner_wins} ta</b>\n"
                            f"<i>{escape(game.p2_name)}ning o‘z raqami esa: {game.p2_secret} edi.</i>\n"
                            f"Ajoyib intellektual jang bo‘ldi! 👏",
                            parse_mode="HTML"
                        )

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
                        hint_icon = "🔼 <b>TEPA (Kattaroq!)</b>"
                    else:
                        game.p2_max = min(game.p2_max, guess_val - 1)
                        hint_icon = "🔽 <b>PAST (Kichikroq!)</b>"

                    # Navbat P1 ga o'tadi
                    game.turn_user_id = game.p1_id
                    next_player_name = game.p1_name
                    target_player_name = game.p2_name

                    await message.answer(
                        f"👤 <b>{escape(game.p2_name)}</b>: <code>{guess_val}</code> ➡️ {hint_icon}\n"
                        f"📊 {escape(game.p2_name)} uchun oraliq: <code>[{game.p2_min} ... {game.p2_max}]</code>\n\n"
                        f"🎯 <b>Navbat:</b> <b>{escape(next_player_name)}</b>!\n"
                        f"<i>{escape(target_player_name)} yashirgan raqamni topish uchun raqam yozing:</i>",
                        parse_mode="HTML"
                    )
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

    # Faqat taklif qilingan P2 qabul qila oladi (agar P2_id 0 bo'lsa, username tekshiriladi)
    u = query.from_user
    if game.p2_id and game.p2_id != u.id:
        await query.answer("❌ Bu taklif sizga emas!", show_alert=True)
        return
    elif not game.p2_id and game.p2_username:
        if not u.username or u.username.lower() != game.p2_username.lower():
            await query.answer("❌ Bu taklif sizga emas!", show_alert=True)
            return

    # P2 ma'lumotlarini aniqlashtirish
    game.p2_id = u.id
    game.p2_name = u.full_name
    game.p2_username = u.username
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

    await query.message.edit_text(
        f"🎯 <b>Jang taklifi qabul qilindi!</b>\n\n"
        f"👤 <b>{escape(game.p1_name)}</b> ⚔️ <b>{escape(game.p2_name)}</b>\n\n"
        f"Quyidan o‘yin oralig‘ini tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )
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

    cleanup_chat_game(game.chat_id)
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

        await query.message.edit_text(
            f"🚀 <b>O‘YIN BOSHLANDI!</b> (Oraliq: 1 — {game.max_range})\n\n"
            f"Ikkala o‘yinchi ham o‘z maxfiy raqamini yashirdi! 🤫\n\n"
            f"🎯 <b>1-navbat:</b> <b>{escape(game.p1_name)}</b>!\n"
            f"<i>{escape(game.p2_name)} yashirgan raqamni topish uchun guruhga raqam yozing:</i>",
            reply_markup=None,
            parse_mode="HTML"
        )
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
