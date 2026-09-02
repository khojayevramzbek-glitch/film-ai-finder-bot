import os
import re
import csv
import html
import time
import asyncio
import logging
import platform
import psutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from bot.config import ADMIN_USERNAMES, GEMINI_API_KEYS, TMDB_API_KEYS, BOT_TOKEN, GEMINI_MODEL
from bot.services.db import (
    DB_PATH,
    get_stats,
    get_recent_users,
    get_all_active_users,
    set_user_ban_status,
    is_user_banned,
    get_active_channels,
    add_sponsor_channel,
    remove_sponsor_channel,
    get_admin_setting,
    set_admin_setting,
    get_user_profile
)
from bot.services.ai_service import gemini_key_pool
from bot.services.groq_service import groq_key_pool
from bot.services.tmdb_service import tmdb_key_pool
from admin_bot.keyboards import (
    get_admin_main_keyboard,
    get_back_keyboard,
    get_server_health_keyboard,
    get_user_profile_keyboard,
    get_ai_settings_keyboard,
    get_broadcast_setup_keyboard,
    make_progress_bar
)

from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    TelegramObject
)

logger = logging.getLogger(__name__)
router = Router()

# Track cluster boot time for uptime calculations
CLUSTER_BOOT_TIME = time.time()


def format_uptime(seconds: float) -> str:
    """Formats uptime into days, hours, minutes, seconds."""
    s = int(seconds)
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    minutes, s = divmod(s, 60)
    parts = []
    if days > 0:
        parts.append(f"{days} kun")
    if hours > 0:
        parts.append(f"{hours} soat")
    parts.append(f"{minutes} daqiqa")
    parts.append(f"{s} soniya")
    return " ".join(parts)


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
            return

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
            return

        # 2. Reject non-private chats (groups, channels)
        chat = data.get("event_chat")
        if chat and chat.type != "private":
            bot = data.get("bot")
            if bot:
                try:
                    await bot.leave_chat(chat.id)
                except Exception:
                    pass
            return

        return await handler(event, data)


# Register Outer Middleware
router.message.outer_middleware(AdminSecurityMiddleware())
router.callback_query.outer_middleware(AdminSecurityMiddleware())


class AdminStates(StatesGroup):
    waiting_for_broadcast_msg = State()
    waiting_for_bc_button = State()
    confirm_broadcast = State()
    waiting_for_inspect_user = State()


@router.message(CommandStart())
async def cmd_admin_start(message: Message, state: FSMContext):
    """Admin bot /start command with security authorization and chat_id binding."""
    await state.clear()
    username = message.from_user.username or "khojayev_ramz"

    # Store admin chat_id for real-time alerts
    set_admin_setting("admin_chat_id", str(message.chat.id))

    text = (
        f"👑 <b>Xush kelibsiz, Boshqaruvchi @{html.escape(username)}!</b>\n\n"
        f"🎬 <b>FilmFinder Boshqaruv Markazi (Enterprise SaaS Edition)</b>\n"
        f"Barcha tizimlar, AI klasterlar va foydalanuvchilar to'liq nazoratingiz ostida:\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "adm:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Returns to admin main menu."""
    await state.clear()
    text = (
        f"👑 <b>FilmFinder Boshqaruv Markazi</b>\n\n"
        f"Barcha tizimlar barqaror ishlamoqda. Kerakli bo'limni tanlang:\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    await callback.answer()


# ====================================================================
# 1. 🖥 SERVER & SYSTEM HEALTH MONITOR
# ====================================================================
@router.callback_query(F.data == "adm:server")
async def cb_server_health(callback: CallbackQuery, bot: Bot):
    """Real-time server diagnostics: CPU, RAM, Uptime, Latency."""
    t0 = time.time()
    try:
        await bot.get_me()
        ping_ms = int((time.time() - t0) * 1000)
    except Exception:
        ping_ms = 999

    # Uptime
    uptime_str = format_uptime(time.time() - CLUSTER_BOOT_TIME)

    # Process Memory & System Memory
    try:
        process = psutil.Process()
        proc_mem_mb = process.memory_info().rss / (1024 * 1024)
        sys_mem = psutil.virtual_memory()
        mem_pct = sys_mem.percent
        mem_bar = make_progress_bar(mem_pct)
        total_ram_gb = sys_mem.total / (1024 * 1024 * 1024)
        used_ram_gb = sys_mem.used / (1024 * 1024 * 1024)
    except Exception:
        proc_mem_mb = 0
        mem_pct = 0
        mem_bar = "🟩🟩⬜️⬜️⬜️⬜️⬜️⬜️"
        total_ram_gb = 1
        used_ram_gb = 0.2

    # CPU
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_bar = make_progress_bar(cpu_pct)
    except Exception:
        cpu_pct = 15.0
        cpu_bar = "🟩⬜️⬜️⬜️⬜️⬜️⬜️⬜️"

    active_model = get_admin_setting("active_ai_model", GEMINI_MODEL)

    health_text = (
        "🖥 <b>SERVER & TIZIM SALOMATLIGI MONITORI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱ <b>Uzluksiz Ishlash (Uptime):</b>\n"
        f"   └ <code>{uptime_str}</code>\n\n"
        f"⚡️ <b>Telegram API Ping / Latency:</b>\n"
        f"   └ <b>{ping_ms} ms</b> {'🟢 Ajoyib' if ping_ms < 150 else '🟡 Qoniqarli'}\n\n"
        f"💾 <b>RAM (Operativ Xotira):</b>\n"
        f"   ├ Jarayon (Bot): <b>{proc_mem_mb:.1f} MB</b>\n"
        f"   ├ Server Jami: <b>{used_ram_gb:.2f} GB / {total_ram_gb:.2f} GB</b>\n"
        f"   └ Holat: <code>[{mem_bar}]</code> <b>{mem_pct}%</b>\n\n"
        f"⚙️ <b>CPU Yuklamasi:</b>\n"
        f"   └ <code>[{cpu_bar}]</code> <b>{cpu_pct}%</b>\n\n"
        f"🌐 <b>Infratuzilma:</b>\n"
        f"   ├ OS: <b>{platform.system()} ({platform.release()})</b>\n"
        f"   ├ Python: <b>{platform.python_version()}</b>\n"
        f"   ├ Faol AI Modeli: <b>{active_model}</b>\n"
        f"   └ Status: <b>24/7 Render Cloud Faol 🟢</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )

    try:
        await callback.message.edit_text(health_text, reply_markup=get_server_health_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(health_text, reply_markup=get_server_health_keyboard(), parse_mode="HTML")
    await callback.answer()


# ====================================================================
# 2. 🔍 USER INSPECTOR & DOSSIER
# ====================================================================
@router.callback_query(F.data == "adm:inspect_user")
async def cb_prompt_user_search(callback: CallbackQuery, state: FSMContext):
    """Prompts admin to enter User ID or @username."""
    await state.set_state(AdminStates.waiting_for_inspect_user)
    text = (
        "🔍 <b>FOYDALANUVCHINI QIDIRISH (Dossier Inspector)</b>\n\n"
        "Foydalanuvchining <b>Telegram ID</b> raqamini yoki <b>@username</b>ini kiriting:\n\n"
        "<i>Masalan:</i>\n"
        "👉 <code>123456789</code>\n"
        "👉 <code>@ali_cinema</code>\n\n"
        "<i>(Bekor qilish uchun /cancel yozing)</i>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(StateFilter(AdminStates.waiting_for_inspect_user), F.text & ~F.text.startswith("/"))
@router.message(Command("user"))
async def handle_user_inspection(message: Message, state: FSMContext):
    """Processes user search input and displays complete dossier card."""
    await state.clear()
    raw_query = message.text.replace("/user", "").strip()
    if not raw_query:
        await message.answer("⚠️ Qidirish uchun ID yoki username kiriting. Masalan: <code>/user 12345678</code>", parse_mode="HTML")
        return

    profile = get_user_profile(raw_query)
    if not profile:
        await message.answer(
            f"❌ <b>Foydalanuvchi topilmadi!</b>\n\n"
            f"<code>{html.escape(raw_query)}</code> bo'yicha bazada hech qanday ma'lumot mavjud emas.\n"
            f"Foydalanuvchi hali botga /start bosmagan bo'lishi mumkin.",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )
        return

    u_id = profile["user_id"]
    u_username = f"@{profile['username']}" if profile.get("username") else "<i>Mavjud emas</i>"
    u_name = html.escape(profile.get("first_name") or "Noma'lum")
    lang = profile.get("language_code", "uz").upper()
    points = profile.get("points", 0)
    is_banned = bool(profile.get("is_banned"))
    ban_status = "🚫 Bloklangan" if is_banned else "🟢 Faol (Ruxsat etilgan)"
    created = str(profile.get("created_at", ""))[:16]
    total_searches = profile.get("total_searches", 0)

    saved_movies = profile.get("saved_movies", [])
    if saved_movies:
        movie_lines = [f"  • {html.escape(m['movie_title'])} ({m.get('release_year') or 'N/A'})" for m in saved_movies[:5]]
        movies_text = "\n".join(movie_lines)
    else:
        movies_text = "  • <i>Hozircha saqlangan filmlar yo'q</i>"

    dossier_text = (
        "📋 <b>FOYDALANUVCHI SHAXSIY DOSYESI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Ism:</b> {u_name}\n"
        f"🔗 <b>Username:</b> {u_username}\n"
        f"🆔 <b>Telegram ID:</b> <code>{u_id}</code>\n"
        f"🌐 <b>Tanlagan Tili:</b> <b>{lang}</b>\n"
        f"📅 <b>Ro'yxatdan O'tgan:</b> <code>{created}</code>\n"
        f"🚫 <b>Holati:</b> <b>{ban_status}</b>\n\n"
        f"🔍 <b>Jami Qidiruvlar Soni:</b> <code>{total_searches} ta</code>\n"
        f"🏆 <b>Viktorina Ballari:</b> <code>{points} ball</code>\n\n"
        f"❤️ <b>Oxirgi Saqlangan Filmlari ({len(saved_movies)} ta):</b>\n"
        f"{movies_text}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )

    await message.answer(
        dossier_text,
        reply_markup=get_user_profile_keyboard(user_id=u_id, is_banned=is_banned),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm:toggle_ban:"))
async def cb_toggle_ban_user(callback: CallbackQuery):
    """Toggles user ban state dynamically from inspector card."""
    user_id = int(callback.data.split(":")[2])
    currently_banned = is_user_banned(user_id)
    new_ban_state = not currently_banned

    set_user_ban_status(user_id, is_banned=new_ban_state)
    alert_msg = f"🚫 Foydalanuvchi ({user_id}) bloklandi!" if new_ban_state else f"🟢 Foydalanuvchi ({user_id}) blokdan ochildi!"
    await callback.answer(alert_msg, show_alert=True)

    # Re-render updated dossier
    profile = get_user_profile(str(user_id))
    if profile:
        u_username = f"@{profile['username']}" if profile.get("username") else "<i>Mavjud emas</i>"
        u_name = html.escape(profile.get("first_name") or "Noma'lum")
        ban_status = "🚫 Bloklangan" if new_ban_state else "🟢 Faol (Ruxsat etilgan)"

        saved_movies = profile.get("saved_movies", [])
        movie_lines = [f"  • {html.escape(m['movie_title'])}" for m in saved_movies[:5]]
        movies_text = "\n".join(movie_lines) if movie_lines else "  • <i>Hozircha yo'q</i>"

        dossier_text = (
            "📋 <b>FOYDALANUVCHI SHAXSIY DOSYESI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>Ism:</b> {u_name}\n"
            f"🔗 <b>Username:</b> {u_username}\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
            f"🚫 <b>Holati:</b> <b>{ban_status}</b>\n\n"
            f"🔍 <b>Jami Qidiruvlar:</b> <code>{profile.get('total_searches', 0)} ta</code>\n"
            f"🏆 <b>Ballari:</b> <code>{profile.get('points', 0)} ball</code>\n\n"
            f"❤️ <b>Oxirgi Saqlangan Filmlari:</b>\n"
            f"{movies_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
        try:
            await callback.message.edit_text(
                dossier_text,
                reply_markup=get_user_profile_keyboard(user_id=user_id, is_banned=new_ban_state),
                parse_mode="HTML"
            )
        except Exception:
            pass


# ====================================================================
# 3. 🤖 AI MODEL SETTINGS & TEMPERATURE SWITCHER
# ====================================================================
@router.callback_query(F.data == "adm:ai_settings")
async def cb_ai_settings(callback: CallbackQuery):
    """Dynamic AI model configuration dashboard."""
    current_model = get_admin_setting("active_ai_model", GEMINI_MODEL)
    try:
        current_temp = float(get_admin_setting("ai_temperature", "0.2"))
    except Exception:
        current_temp = 0.2

    text = (
        "🤖 <b>SUN'IY INTELLEKT (AI) SOZLAMALARI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🟢 <b>Faol Qidiruv Modeli:</b> <code>{current_model}</code>\n"
        f"🌡 <b>Ijodiylik Darajasi (Temperature):</b> <code>{current_temp}</code>\n\n"
        "Quyidagi tugmalar orqali serverni qayta ishga tushirmasdan, "
        "modelni va uning tahlil aniqligini jonli o'zgartirishingiz mumkin:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_ai_settings_keyboard(current_model, current_temp),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_ai_settings_keyboard(current_model, current_temp),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:set_model:"))
async def cb_set_ai_model(callback: CallbackQuery):
    """Switches active AI model."""
    new_model = callback.data.split(":")[2]
    set_admin_setting("active_ai_model", new_model)
    await callback.answer(f"✅ AI modeli o'zgartirildi: {new_model}", show_alert=True)
    await cb_ai_settings(callback)


@router.callback_query(F.data.startswith("adm:set_temp:"))
async def cb_set_ai_temp(callback: CallbackQuery):
    """Updates AI creativity temperature."""
    new_temp = callback.data.split(":")[2]
    set_admin_setting("ai_temperature", new_temp)
    await callback.answer(f"✅ AI harorati o'rnatildi: {new_temp}", show_alert=True)
    await cb_ai_settings(callback)


# ====================================================================
# 4. 🔔 LIVE ADMIN NOTIFICATIONS TOGGLE
# ====================================================================
@router.callback_query(F.data == "adm:toggle_alerts")
async def cb_toggle_alerts(callback: CallbackQuery):
    """Toggles real-time new user join notifications."""
    current = get_admin_setting("live_alerts_enabled", "1")
    new_val = "0" if current == "1" else "1"
    set_admin_setting("live_alerts_enabled", new_val)

    status_txt = "Yoqildi (Faol) 🟢" if new_val == "1" else "O'chirildi 🔴"
    await callback.answer(f"🔔 Jonli bildirishnomalar: {status_txt}", show_alert=True)

    # Refresh main menu with updated button text
    text = (
        f"👑 <b>FilmFinder Boshqaruv Markazi</b>\n\n"
        f"Barcha tizimlar barqaror ishlamoqda. Kerakli bo'limni tanlang:\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    except Exception:
        pass


# ====================================================================
# 5. 📢 SMART BROADCAST V2.0 (BUTTONS & TEST SEND)
# ====================================================================
@router.callback_query(F.data == "adm:broadcast")
async def cb_start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Initiates interactive broadcast creation."""
    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    text = (
        "📢 <b>XABAR TARQATISH V2.0 (Smart Composer)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan post/xabarni yuboring:\n\n"
        "• <i>Matn, Rasm, Video yoki Forward qilingan xabar yuborishingiz mumkin.</i>\n"
        "• <i>Keyingi qadamda xabarga chiroyli havolali tugma qo'shishingiz mumkin bo'ladi.</i>\n\n"
        "<i>(Bekor qilish uchun /cancel deb yozing)</i>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminStates))
async def cmd_cancel_broadcast(message: Message, state: FSMContext):
    """Cancels ongoing broadcast or inspector setup."""
    await state.clear()
    await message.answer("❌ Amaliyot bekor qilindi.", reply_markup=get_admin_main_keyboard())


@router.message(StateFilter(AdminStates.waiting_for_broadcast_msg))
async def handle_broadcast_message_input(message: Message, state: FSMContext):
    """Receives broadcast message and opens options (Add Button, Test Send, Broadcast)."""
    await state.update_data(
        chat_id=message.chat.id,
        message_id=message.message_id,
        button_text="",
        button_url=""
    )
    await state.set_state(AdminStates.confirm_broadcast)

    active_users = get_all_active_users()
    total_count = len(active_users)

    preview_note = (
        f"📢 <b>Xabar qabul qilindi!</b>\n\n"
        f"👥 Yuboriladigan foydalanuvchilar soni: <b>{total_count} ta</b>\n\n"
        f"Endi xabarga <b>URL tugma</b> qo'shishingiz, o'zingizga <b>sinov tariqasida</b> yuborib ko'rishingiz yoki barchaga tarqatishingiz mumkin:"
    )
    await message.reply(
        preview_note,
        reply_markup=get_broadcast_setup_keyboard(has_button=False),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm:bc_add_btn", StateFilter(AdminStates.confirm_broadcast))
async def cb_prompt_broadcast_button(callback: CallbackQuery, state: FSMContext):
    """Prompts admin for inline button text & url."""
    await state.set_state(AdminStates.waiting_for_bc_button)
    prompt_text = (
        "🔘 <b>TUGMA (URL LINK) QO'SHISH</b>\n\n"
        "Tugma matni va havolasini <b>|</b> belgisi bilan ajratib yuboring:\n\n"
        "<i>Format:</i> <code>Tugma Nomi | Havola</code>\n\n"
        "<i>Misol:</i>\n"
        "👉 <code>Kanalga a'zo bo'lish | https://t.me/khojayev_gaz</code>\n"
        "👉 <code>Kinoni ko'rish | https://google.com</code>"
    )
    try:
        await callback.message.edit_text(prompt_text, parse_mode="HTML")
    except Exception:
        await callback.message.answer(prompt_text, parse_mode="HTML")
    await callback.answer()


@router.message(StateFilter(AdminStates.waiting_for_bc_button), F.text & ~F.text.startswith("/"))
async def handle_button_input(message: Message, state: FSMContext):
    """Parses button title and URL."""
    text = message.text.strip()
    if "|" not in text:
        await message.answer("⚠️ Iltimos, formatga rioya qiling: <code>Tugma Nomi | Havola</code>", parse_mode="HTML")
        return

    parts = [p.strip() for p in text.split("|", maxsplit=1)]
    btn_label, btn_url = parts[0], parts[1]

    if not btn_url.startswith("http://") and not btn_url.startswith("https://") and not btn_url.startswith("t.me/"):
        await message.answer("⚠️ Havola noto'g'ri (https:// bilan boshlanishi kerak).", parse_mode="HTML")
        return

    if btn_url.startswith("t.me/"):
        btn_url = "https://" + btn_url

    await state.update_data(button_text=btn_label, button_url=btn_url)
    await state.set_state(AdminStates.confirm_broadcast)

    await message.answer(
        f"✅ <b>Tugma biriktirildi:</b>\n"
        f"[{html.escape(btn_label)}] ➡️ <code>{btn_url}</code>\n\n"
        f"Tayyor bo'lsangiz, sinab ko'ring yoki barchaga tarqating:",
        reply_markup=get_broadcast_setup_keyboard(has_button=True),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm:bc_rm_btn", StateFilter(AdminStates.confirm_broadcast))
async def cb_remove_broadcast_button(callback: CallbackQuery, state: FSMContext):
    """Removes attached button."""
    await state.update_data(button_text="", button_url="")
    await callback.answer("🗑 Tugma olib tashlandi!", show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=get_broadcast_setup_keyboard(has_button=False))
    except Exception:
        pass


@router.callback_query(F.data == "adm:bc_test_send", StateFilter(AdminStates.confirm_broadcast))
async def cb_test_send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Sends a test copy of the broadcast to the admin himself."""
    data = await state.get_data()
    from_chat_id = data.get("chat_id")
    msg_id = data.get("message_id")
    btn_text = data.get("button_text")
    btn_url = data.get("button_url")

    reply_markup = None
    if btn_text and btn_url:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, url=btn_url)]
        ])

    try:
        await bot.copy_message(
            chat_id=callback.from_user.id,
            from_chat_id=from_chat_id,
            message_id=msg_id,
            reply_markup=reply_markup
        )
        await callback.answer("👁 Sinov xabari sizga yuborildi! Tekshirib ko'ring.", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)


@router.callback_query(F.data == "adm:cancel_broadcast", StateFilter(AdminStates.confirm_broadcast))
async def cb_cancel_broadcast_btn(callback: CallbackQuery, state: FSMContext):
    """Cancels broadcast setup."""
    await state.clear()
    await callback.message.edit_text("❌ Xabar tarqatish bekor qilindi.", reply_markup=get_admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:confirm_broadcast", StateFilter(AdminStates.confirm_broadcast))
async def cb_execute_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Executes live broadcast with progress indicators and optional inline URL buttons."""
    data = await state.get_data()
    from_chat_id = data.get("chat_id")
    msg_id = data.get("message_id")
    btn_text = data.get("button_text")
    btn_url = data.get("button_url")

    reply_markup = None
    if btn_text and btn_url:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, url=btn_url)]
        ])

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
                message_id=msg_id,
                reply_markup=reply_markup
            )
            success_cnt += 1
        except Exception:
            blocked_cnt += 1

        if idx % 25 == 0 or idx == total_users:
            pct = (idx / total_users) * 100
            p_bar = make_progress_bar(pct)
            try:
                await progress_msg.edit_text(
                    f"🚀 <b>Xabar tarqatilmoqda... ({idx}/{total_users})</b>\n\n"
                    f"<code>[{p_bar}] {pct:.1f}%</code>\n"
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


# ====================================================================
# 6. 📊 LIVE STATISTICS
# ====================================================================
@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery):
    """Renders comprehensive live statistics with visual bars."""
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


# ====================================================================
# 7. 🔑 API KEYS MONITOR
# ====================================================================
@router.callback_query(F.data == "adm:keys")
async def cb_api_keys(callback: CallbackQuery):
    """Renders real-time status of Gemini 15 keys, Groq 10 keys, and TMDb keys."""
    gemini_status = gemini_key_pool.get_pool_status()
    groq_status = groq_key_pool.get_pool_status()
    tmdb_status = tmdb_key_pool.get_pool_status()

    lines = [
        "🔑 <b>API KALITLARI JONLI MONITORI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n",
        f"⚡️ <b>Groq AI (10 Kalit - Random, Actor, Quiz, Roleplay):</b>",
        f"• Jami: <b>{groq_status['total']} ta</b> | 🟢 Faol: <b>{groq_status['active']} ta</b> | 🟡 Kutishda: <b>{groq_status['cooldown']} ta</b>\n",
        f"🤖 <b>Google Gemini AI (15 Kalit - Video & Vision Qidiruv):</b>",
        f"• Jami: <b>{gemini_status['total']} ta</b> | 🟢 Faol: <b>{gemini_status['active']} ta</b> | 🟡 Kutishda: <b>{gemini_status['cooldown']} ta</b>\n",
        f"🎬 <b>TMDb Metadata Kalitlari:</b>",
        f"• Jami: <b>{tmdb_status['total']} ta</b> | 🟢 Faol: <b>{tmdb_status['active']} ta</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    key_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Barcha Kalitlarni Zudlik Bilan Tiklash", callback_data="adm:reset_keys")],
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


# ====================================================================
# 8. 📢 SPONSOR CHANNELS (HOMIY KANALLAR)
# ====================================================================
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
    lines.append("👉 <code>/addchannel @khojayev_gaz</code>\n")
    lines.append("⚠️ <i>Muhim: Asosiy botingiz (<b>@FilmAiFinderbot</b>) o'sha kanalga <b>Administrator</b> qilib qo'shilgan bo'lishi kerak!</i>")

    buttons.append([InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")])

    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


@router.message(Command("addchannel"))
async def cmd_add_channel(message: Message, bot: Bot):
    """Intelligent 1-click sponsor channel adder."""
    text = message.text.replace("/addchannel", "").strip()
    if not text:
        await message.answer(
            "⚠️ <b>Kanal manzilini kiriting!</b>\n\nMasalan:\n<code>/addchannel @khojayev_gaz</code>",
            parse_mode="HTML"
        )
        return

    raw_input = text.split()[0]
    channel_username = raw_input.replace("https://t.me/", "").replace("t.me/", "").lstrip("@").strip()

    if not channel_username:
        await message.answer("❌ Kanal username yoki havolasi noto'g'ri.", parse_mode="HTML")
        return

    target_chat = f"@{channel_username}" if not channel_username.startswith("-100") else channel_username
    channel_url = f"https://t.me/{channel_username.lstrip('@')}"

    from aiogram import Bot as SearchBot
    main_bot = SearchBot(token=BOT_TOKEN)

    try:
        chat = await main_bot.get_chat(target_chat)
        ch_id = str(chat.id)
        ch_title = chat.title or channel_username

        me = await main_bot.get_me()
        try:
            member = await main_bot.get_chat_member(chat_id=chat.id, user_id=me.id)
            if member.status not in ["administrator", "creator"]:
                await message.answer(
                    f"⚠️ <b>E'tibor bering:</b>\n\n"
                    f"<b>@{me.username}</b> boti <b>'{html.escape(ch_title)}'</b> kanaliga <b>Administrator</b> qilinmagan!",
                    parse_mode="HTML"
                )
        except Exception:
            pass

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
        await message.answer(
            f"❌ <b>Kanal topilmadi!</b>\n\n"
            f"Iltimos, avval <b>@FilmAiFinderbot</b> ni kanalga <b>Administrator</b> qilib qo'shing va qayta yuboring:\n"
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


# ====================================================================
# 9. 👥 RECENT USERS
# ====================================================================
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
    lines.append("💡 <i>Foydalanuvchini to'liq tekshirish uchun: '🔍 Foydalanuvchi Dosyesi' tugmasini bosing.</i>")

    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=get_back_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=get_back_keyboard(), parse_mode="HTML")
    await callback.answer()


# ====================================================================
# 10. 📥 EXPORT DATABASE FILE
# ====================================================================
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
