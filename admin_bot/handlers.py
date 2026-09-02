import os
import re
import csv
import html
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

from bot.config import ADMIN_USERNAMES, GEMINI_API_KEYS, TMDB_API_KEYS, BOT_TOKEN
from bot.services.db import (
    DB_PATH,
    get_stats,
    get_recent_users,
    get_all_active_users,
    set_user_ban_status,
    is_user_banned,
    get_active_channels,
    add_sponsor_channel,
    remove_sponsor_channel
)
from bot.services.ai_service import gemini_key_pool
from bot.services.groq_service import groq_key_pool
from bot.services.tmdb_service import tmdb_key_pool
from admin_bot.keyboards import (
    get_admin_main_keyboard,
    get_back_keyboard,
    get_broadcast_confirm_keyboard
)

from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, TelegramObject

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int, username: str = "") -> bool:
    """Checks if the sender is the authorized admin (@khojayev_ramz)."""
    clean_username = (username or "").lstrip("@").lower()
    return clean_username in [u.lower() for u in ADMIN_USERNAMES]


class AdminSecurityMiddleware(BaseMiddleware):
    """
    Ironclad security middleware for FilmFinder Admin Bot.
    Enforces strict access control:
    - ONLY @khojayev_ramz can interact with this bot.
    - All unauthorized access attempts from ANY other user are completely rejected and logged.
    - Automatically leaves any unauthorized groups/channels.
    """
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if not user:
            return  # Drop update silently

        username = (user.username or "").lstrip("@").lower()
        allowed_admins = [u.lower() for u in ADMIN_USERNAMES]

        # 1. Reject anyone who is not in ADMIN_USERNAMES (@khojayev_ramz)
        if username not in allowed_admins:
            logger.warning(
                f"🚨 [BLOCKED UNAUTHORIZED ACCESS] User ID: {user.id} | "
                f"Username: @{user.username} | Name: {user.full_name}"
            )
            if isinstance(event, Message):
                await event.answer(
                    "⛔️ <b>KIRISH TAQIQLANGAN!</b>\n\n"
                    "Ushbu bot shaxsiy yopiq tizim hisoblanadi va faqat <b>@khojayev_ramz</b> uchun ishlaydi.\n\n"
                    "<i>Begona foydalanuvchilarning barcha so'rovlari avtomatik tarzda bloklanadi.</i>",
                    parse_mode="HTML"
                )
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(
                        "⛔️ Kirish taqiqlangan! Bu bot faqat @khojayev_ramz uchun.",
                        show_alert=True
                    )
                except Exception:
                    pass
            return  # STOP! Do not execute any handler

        # 2. Reject non-private chats (groups, channels)
        chat = data.get("event_chat")
        if chat and chat.type != "private":
            bot = data.get("bot")
            if bot:
                try:
                    await bot.leave_chat(chat.id)
                except Exception:
                    pass
            return  # Stop execution in non-private chats

        return await handler(event, data)


# Register Ironclad Security Middleware as Outer Middleware
router.message.outer_middleware(AdminSecurityMiddleware())
router.callback_query.outer_middleware(AdminSecurityMiddleware())


class AdminStates(StatesGroup):
    waiting_for_broadcast_msg = State()
    confirm_broadcast = State()


@router.message(CommandStart())
async def cmd_admin_start(message: Message, state: FSMContext):
    """Admin bot /start command with security authorization."""
    await state.clear()
    username = message.from_user.username or ""

    text = (
        f"👑 <b>Xush kelibsiz, Admin @{html.escape(username)}!</b>\n\n"
        f"🎬 <b>FilmFinder Boshqaruv Markazi</b>ga ulandingiz.\n"
        f"Quyidagi tugmalar orqali botingizni to'liq nazorat qilishingiz mumkin:"
    )
    await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "adm:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Returns to admin main menu."""
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    username = callback.from_user.username or ""

    if not is_admin(user_id, username):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    text = (
        f"👑 <b>FilmFinder Boshqaruv Markazi</b>\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    await callback.answer()


# 1. LIVE STATISTICS
@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery):
    """Renders comprehensive live statistics."""
    stats = get_stats()

    total_users = stats.get("total_users", 0)
    today_users = stats.get("today_users", 0)
    banned_users = stats.get("banned_users", 0)
    total_searches = stats.get("total_searches", 0)
    today_searches = stats.get("today_searches", 0)
    saved_count = stats.get("saved_count", 0)
    alerts_count = stats.get("alerts_count", 0)
    lang_counts = stats.get("lang_counts", {})
    search_types = stats.get("search_types", {})

    lang_labels = {
        "uz": "🇺🇿 O'zbekcha (Lotin)",
        "uz_kr": "🇺🇿 Ўзбекча (Кирилл)",
        "ru": "🇷🇺 Русский",
        "en": "🇬🇧 English"
    }
    lang_lines = []
    for l_code, count in lang_counts.items():
        pct = (count / total_users * 100) if total_users > 0 else 0
        l_name = lang_labels.get(l_code, l_code)
        lang_lines.append(f"  • {l_name}: <b>{count} ta</b> ({pct:.1f}%)")

    lang_text = "\n".join(lang_lines) if lang_lines else "  • Hozircha ma'lumot yo'q"

    type_lines = []
    for s_type, cnt in search_types.items():
        type_lines.append(f"  • {s_type.title()}: <b>{cnt} ta</b>")
    type_text = "\n".join(type_lines) if type_lines else "  • Hozircha qidiruvlar yo'q"

    msg_text = (
        "📊 <b>FILMFINDER JONLI STATISTIKASI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Jami Foydalanuvchilar:</b> <code>{total_users} ta</code>\n"
        f"🆕 <b>Bugun Qo'shilganlar:</b> <code>+{today_users} ta</code>\n"
        f"🚫 <b>Bloklanganlar:</b> <code>{banned_users} ta</code>\n\n"
        f"🔍 <b>Jami Qidiruvlar:</b> <code>{total_searches} ta</code>\n"
        f"⚡️ <b>Bugungi Qidiruvlar:</b> <code>{today_searches} ta</code>\n"
        f"❤️ <b>Saqlangan Kinolar:</b> <code>{saved_count} ta</code>\n"
        f"🔔 <b>Premyera Eslatmalari:</b> <code>{alerts_count} ta</code>\n\n"
        "🌐 <b>Tillar Taqsimoti:</b>\n"
        f"{lang_text}\n\n"
        "📂 <b>Qidiruv Turlari:</b>\n"
        f"{type_text}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await callback.message.edit_text(msg_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(msg_text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


# 2. API KEYS MONITOR
@router.callback_query(F.data == "adm:keys")
async def cb_api_keys(callback: CallbackQuery):
    """Renders real-time status of Gemini 15 keys, Groq 10 keys, and TMDb keys."""
    gemini_status = gemini_key_pool.get_pool_status()
    groq_status = groq_key_pool.get_pool_status()
    tmdb_status = tmdb_key_pool.get_pool_status()

    lines = [
        "🔑 <b>API KALITLARI JONLI MONITORI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n",
        f"⚡️ <b>Groq AI (Llama 3.3 70B - Random & Quiz):</b>",
        f"• Jami: <b>{groq_status['total']} ta</b> | 🟢 Faol: <b>{groq_status['active']} ta</b> | 🟡 Kutishda: <b>{groq_status['cooldown']} ta</b>\n",
        f"🤖 <b>Google Gemini AI (Video & Vision Qidiruv):</b>",
        f"• Jami: <b>{gemini_status['total']} ta</b> | 🟢 Faol: <b>{gemini_status['active']} ta</b> | 🟡 Kutishda: <b>{gemini_status['cooldown']} ta</b>\n",
        f"🎬 <b>TMDb Metadata Kalitlari:</b>",
        f"• Jami: <b>{tmdb_status['total']} ta</b> | 🟢 Faol: <b>{tmdb_status['active']} ta</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    key_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Barcha Kalitlarni Tiklash", callback_data="adm:reset_keys")],
        [InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")]
    ])

    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=key_kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=key_kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "adm:reset_keys")
async def cb_reset_keys(callback: CallbackQuery):
    """Instantly clears all cooldown timers on all API keys."""
    g_cnt = gemini_key_pool.reset_all_cooldowns()
    gr_cnt = groq_key_pool.reset_all_cooldowns()
    t_cnt = tmdb_key_pool.reset_all_cooldowns()
    await callback.answer(f"✅ Barcha {g_cnt + gr_cnt + t_cnt} ta kalitlar zudlik bilan faollashtirildi!", show_alert=True)
    await cb_api_keys(callback)


# 3. SPONSOR CHANNELS (HOMIY KANALLAR)
@router.callback_query(F.data == "adm:channels")
async def cb_sponsor_channels(callback: CallbackQuery):
    """Manages sponsor channels for mandatory subscription."""
    channels = get_active_channels()

    lines = [
        "📢 <b>HOMIY KANALLAR BOSHQARUVI (Majburiy Obuna)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    buttons = []
    if not channels:
        lines.append("<i>Hozircha hech qanday homiy kanal qo'shilmagan (Barcha foydalanuvchilar to'siqsiz kirmoqda).</i>\n")
    else:
        lines.append("🟢 <b>Faol Homiy Kanallar:</b>")
        for idx, ch in enumerate(channels, 1):
            c_id = ch["channel_id"]
            c_title = html.escape(ch["channel_title"])
            c_url = ch["channel_url"]
            lines.append(f"<b>{idx}. {c_title}</b> (<code>{c_id}</code>)\n   🔗 <a href='{c_url}'>{c_url}</a>")
            buttons.append([
                InlineKeyboardButton(text=f"🗑 O'chirish: {c_title[:20]}", callback_data=f"adm:del_ch:{ch['id']}")
            ])
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("➕ <b>Kanal qo'shish juda oson:</b>")
    lines.append("Shunchaki buyruqni yuboring:")
    lines.append("👉 <code>/addchannel @khojayev_gaz</code>")
    lines.append("yoki")
    lines.append("👉 <code>/addchannel https://t.me/khojayev_gaz</code>")
    lines.append("\n⚠️ <i>Muhim qoida: Asosiy botingiz (<b>@FilmAiFinderbot</b>) o'sha kanalga <b>Administrator</b> qilib qo'shilgan bo'lishi kerak!</i>")

    buttons.append([InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")])

    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


@router.message(Command("addchannel"))
async def cmd_add_channel(message: Message, bot: Bot):
    """
    Intelligent 1-click sponsor channel adder.
    Accepts: /addchannel @username or /addchannel https://t.me/username or /addchannel -100xxx Title URL
    """
    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username or ""
    if not is_admin(user_id, username):
        return

    text = message.text.replace("/addchannel", "").strip()
    if not text:
        await message.answer(
            "⚠️ <b>Kanal manzilini kiriting!</b>\n\nMasalan:\n<code>/addchannel @khojayev_gaz</code>\nyoki\n<code>/addchannel https://t.me/khojayev_gaz</code>",
            parse_mode="HTML"
        )
        return

    # Extract username or URL
    raw_input = text.split()[0]
    channel_username = raw_input.replace("https://t.me/", "").replace("t.me/", "").lstrip("@").strip()

    if not channel_username:
        await message.answer("❌ Kanal username yoki havolasi noto'g'ri.", parse_mode="HTML")
        return

    target_chat = f"@{channel_username}" if not channel_username.startswith("-100") else channel_username
    channel_url = f"https://t.me/{channel_username.lstrip('@')}"

    # Use main search bot to verify and get channel details
    from aiogram import Bot as SearchBot
    main_bot = SearchBot(token=BOT_TOKEN)

    try:
        chat = await main_bot.get_chat(target_chat)
        ch_id = str(chat.id)
        ch_title = chat.title or channel_username

        # Verify bot is administrator in the channel
        me = await main_bot.get_me()
        try:
            member = await main_bot.get_chat_member(chat_id=chat.id, user_id=me.id)
            if member.status not in ["administrator", "creator"]:
                await message.answer(
                    f"⚠️ <b>E'tibor bering:</b>\n\n"
                    f"<b>@{me.username}</b> boti <b>'{html.escape(ch_title)}'</b> kanaliga <b>Administrator</b> qilinmagan!\n\n"
                    f"Foydalanuvchilar obunasini tekshirishi uchun botni kanalga admin qilib qo'shing.",
                    parse_mode="HTML"
                )
        except Exception:
            pass

        # Save to database
        add_sponsor_channel(channel_id=ch_id, channel_title=ch_title, channel_url=channel_url)

        await message.answer(
            f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📢 <b>Nomi:</b> {html.escape(ch_title)}\n"
            f"🆔 <b>ID:</b> <code>{ch_id}</code>\n"
            f"🔗 <b>Havola:</b> {channel_url}\n\n"
            f"Endi barcha yangi foydalanuvchilar botdan foydalanishdan oldin ushbu kanalga a'zo bo'lishadi!",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"[AddChannel Error] {e}")
        # Fallback: if user provided custom title
        parts = text.split(maxsplit=2)
        if len(parts) >= 3:
            ch_id = parts[0]
            ch_title = parts[1]
            ch_url = parts[2]
            add_sponsor_channel(channel_id=ch_id, channel_title=ch_title, channel_url=ch_url)
            await message.answer(f"✅ <b>'{html.escape(ch_title)}' kanali qo'shildi!</b>", parse_mode="HTML")
        else:
            await message.answer(
                f"❌ <b>Kanal topilmadi!</b>\n\n"
                f"Iltimos, avval <b>@FilmAiFinderbot</b> ni o'sha kanalga <b>Administrator</b> qilib qo'shing va qayta yuboring:\n"
                f"<code>/addchannel @{channel_username}</code>",
                parse_mode="HTML"
            )
    finally:
        await main_bot.session.close()


@router.callback_query(F.data.startswith("adm:del_ch:"))
async def cb_del_channel(callback: CallbackQuery):
    """Deletes sponsor channel by database ID."""
    ch_db_id = callback.data.split(":")[2]
    remove_sponsor_channel(ch_db_id)
    await callback.answer("🗑 Kanal muvaffaqiyatli o'chirildi!", show_alert=True)
    await cb_sponsor_channels(callback)


# 4. RECENT USERS & MANAGEMENT
@router.callback_query(F.data == "adm:users")
async def cb_recent_users(callback: CallbackQuery):
    """Displays recent users list."""
    users = get_recent_users(limit=10)
    lines = [
        "👥 <b>OXIRGI RO'YXATDAN O'TGAN FOYDALANUVCHILAR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    for idx, u in enumerate(users, 1):
        u_id = u["user_id"]
        lang = u["language_code"]
        banned = "🚫 Bloklangan" if u.get("is_banned") else "🟢 Faol"
        points = u.get("points", 0)
        created = str(u.get("created_at", ""))[:16]
        lines.append(f"<b>{idx}. ID:</b> <code>{u_id}</code> | {lang.upper()} | {points} ball | {banned}\n   <i>Sana: {created}</i>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <i>Foydalanuvchini bloklash yoki ochish uchun: /ban ID yoki /unban ID yozing.</i>")

    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


# 5. EXPORT DATABASE FILE
@router.callback_query(F.data == "adm:export_db")
async def cb_export_db(callback: CallbackQuery):
    """Exports SQLite DB and CSV list to Admin."""
    await callback.answer("⏳ Baza fayli tayyorlanmoqda...", show_alert=False)

    if not DB_PATH.exists():
        await callback.message.answer("❌ Baza fayli topilmadi.")
        return

    csv_path = Path("downloads") / "users_export.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        users = get_recent_users(limit=10000)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "language_code", "is_banned", "points", "created_at"])
            for u in users:
                writer.writerow([u["user_id"], u["language_code"], u["is_banned"], u.get("points", 0), u["created_at"]])

        db_file = FSInputFile(str(DB_PATH), filename="filmfinder_users.db")
        await callback.message.answer_document(db_file, caption="📁 <b>Asosiy SQLite Ma'lumotlar Bazasi (users.db)</b>", parse_mode="HTML")

        csv_file = FSInputFile(str(csv_path), filename="users_export.csv")
        await callback.message.answer_document(csv_file, caption="📊 <b>Foydalanuvchilar Ro'yxati (Excel / CSV)</b>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"[Export Error] {e}")
        await callback.message.answer(f"❌ Faylni yuborishda xatolik: {e}")
    finally:
        if csv_path.exists():
            csv_path.unlink()


# 6. BROADCAST (XABAR TARQATISH)
@router.callback_query(F.data == "adm:broadcast")
async def cb_start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Initiates broadcast state."""
    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    text = (
        "📢 <b>HAMMAGA XABAR TARQATISH</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing yoki fayl/rasm/video yuboring:\n\n"
        "<i>(Bekor qilish uchun /cancel yozing)</i>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminStates))
async def cmd_cancel_broadcast(message: Message, state: FSMContext):
    """Cancels ongoing broadcast setup."""
    await state.clear()
    await message.answer("❌ Xabar tarqatish bekor qilindi.", reply_markup=get_admin_main_keyboard())


@router.message(StateFilter(AdminStates.waiting_for_broadcast_msg))
async def handle_broadcast_content(message: Message, state: FSMContext):
    """Stores the message to broadcast and asks for confirmation."""
    await state.update_data(
        chat_id=message.chat.id,
        message_id=message.message_id
    )
    await state.set_state(AdminStates.confirm_broadcast)

    active_users = get_all_active_users()
    total_count = len(active_users)

    await message.reply(
        f"📢 <b>Xabar qabul qilindi!</b>\n\n"
        f"Jami yuboriladigan foydalanuvchilar soni: <b>{total_count} ta</b>.\n\n"
        f"Xabarni hoziroq barchaga tarqataylikmi?",
        reply_markup=get_broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm:cancel_broadcast", StateFilter(AdminStates.confirm_broadcast))
async def cb_cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancels broadcast from button."""
    await state.clear()
    await callback.message.edit_text("❌ Xabar tarqatish bekor qilindi.", reply_markup=get_admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:confirm_broadcast", StateFilter(AdminStates.confirm_broadcast))
async def cb_execute_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Executes live broadcast to all users with progress updates."""
    data = await state.get_data()
    from_chat_id = data.get("chat_id")
    msg_id = data.get("message_id")

    await state.clear()
    active_users = get_all_active_users()
    total_users = len(active_users)

    if total_users == 0:
        await callback.message.edit_text("⚠️ Bazada faol foydalanuvchilar mavjud emas.", reply_markup=get_admin_main_keyboard())
        return

    progress_msg = await callback.message.edit_text(
        f"🚀 <b>Xabar tarqatish boshlandi...</b>\n\n"
        f"Jami: <code>{total_users} ta</code>\n"
        f"Yuborildi: <code>0</code> | Bloklagan: <code>0</code>",
        parse_mode="HTML"
    )

    success_cnt = 0
    blocked_cnt = 0

    for idx, user_id in enumerate(active_users, 1):
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=msg_id
            )
            success_cnt += 1
        except Exception:
            blocked_cnt += 1

        if idx % 25 == 0 or idx == total_users:
            try:
                await progress_msg.edit_text(
                    f"🚀 <b>Xabar tarqatilmoqda... ({idx}/{total_users})</b>\n\n"
                    f"✅ Yuborildi: <code>{success_cnt} ta</code>\n"
                    f"🚫 Bloklagan: <code>{blocked_cnt} ta</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await asyncio.sleep(0.05)

    summary_text = (
        "✅ <b>XABAR TARQATISH YAKUNLANDI!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Jami qamrov: <b>{total_users} ta</b>\n"
        f"✅ Muvaffaqiyatli yetkazildi: <b>{success_cnt} ta</b>\n"
        f"🚫 Botni bloklaganlar: <b>{blocked_cnt} ta</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await progress_msg.edit_text(summary_text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    await callback.answer("✅ Xabar barchaga yuborildi!", show_alert=True)


# 7. BAN / UNBAN COMMANDS
@router.message(Command("ban"))
async def cmd_ban_user(message: Message):
    """Bans user by ID: /ban 12345678."""
    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username or ""
    if not is_admin(user_id, username):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Foydalanish: <code>/ban 12345678</code>", parse_mode="HTML")
        return

    target_id = int(parts[1])
    set_user_ban_status(target_id, is_banned=True)
    await message.answer(f"🚫 <b>Foydalanuvchi {target_id} muvaffaqiyatli bloklandi!</b>", parse_mode="HTML")


@router.message(Command("unban"))
async def cmd_unban_user(message: Message):
    """Unbans user by ID: /unban 12345678."""
    user_id = message.from_user.id if message.from_user else 0
    username = message.from_user.username or ""
    if not is_admin(user_id, username):
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ Foydalanish: <code>/unban 12345678</code>", parse_mode="HTML")
        return

    target_id = int(parts[1])
    set_user_ban_status(target_id, is_banned=False)
    await message.answer(f"✅ <b>Foydalanuvchi {target_id} blokdan chiqarildi!</b>", parse_mode="HTML")
