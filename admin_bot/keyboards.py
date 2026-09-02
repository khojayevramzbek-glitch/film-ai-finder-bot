from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.db import get_admin_setting


def make_progress_bar(percent: float, total_blocks: int = 8) -> str:
    """Creates visual progress bar: [🟩🟩🟩⬜️⬜️⬜️⬜️⬜️]."""
    filled = int(round((percent / 100) * total_blocks))
    filled = max(0, min(total_blocks, filled))
    empty = total_blocks - filled
    return "🟩" * filled + "⬜️" * empty


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Enterprise Bento-Grid Control Panel Dashboard keyboard."""
    live_alerts = get_admin_setting("live_alerts_enabled", "1")
    alerts_status = "Yoqilgan 🟢" if live_alerts == "1" else "O'chirilgan 🔴"

    buttons = [
        # Row 1: Core Health & Metrics
        [
            InlineKeyboardButton(text="📊 Jonli Statistika", callback_data="adm:stats"),
            InlineKeyboardButton(text="🖥 Server Salomatligi", callback_data="adm:server"),
        ],
        # Row 2: Intelligence & Keys
        [
            InlineKeyboardButton(text="🔑 API Kalitlar", callback_data="adm:keys"),
            InlineKeyboardButton(text="🤖 AI Sozlamalari", callback_data="adm:ai_settings"),
        ],
        # Row 3: Audience Management
        [
            InlineKeyboardButton(text="🔍 Foydalanuvchi Dosyesi", callback_data="adm:inspect_user"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users"),
        ],
        # Row 4: Growth & Channel Gate
        [
            InlineKeyboardButton(text="📢 Xabar Tarqatish v2.0", callback_data="adm:broadcast"),
            InlineKeyboardButton(text="📢 Homiy Kanallar", callback_data="adm:channels"),
        ],
        # Row 5: Real-time Alerts & Data Backup
        [
            InlineKeyboardButton(text=f"🔔 Bildirishnoma: {alerts_status}", callback_data="adm:toggle_alerts"),
            InlineKeyboardButton(text="📥 Baza Eksporti", callback_data="adm:export_db"),
        ],
        # Row 6: Emergency Key Flush
        [
            InlineKeyboardButton(text="🔄 Barcha Kalitlarni Zudlik Bilan Tiklash", callback_data="adm:reset_keys"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Back to main admin menu button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")]
    ])


def get_server_health_keyboard() -> InlineKeyboardMarkup:
    """Server health refresh and back buttons."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash (Refresh)", callback_data="adm:server")],
        [InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")]
    ])


def get_user_profile_keyboard(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    """Actions for a specific inspected user."""
    ban_btn_text = "🟢 Blokdan Chiqarish (Unban)" if is_banned else "🚫 Bloklash (Ban)"
    ban_cb = f"adm:toggle_ban:{user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ban_btn_text, callback_data=ban_cb)],
        [InlineKeyboardButton(text="🔍 Boshqa Foydalanuvchini Qidirish", callback_data="adm:inspect_user")],
        [InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")]
    ])


def get_ai_settings_keyboard(current_model: str, current_temp: float) -> InlineKeyboardMarkup:
    """Dynamic AI model selection and creativity sliders."""
    models = [
        ("gemini-3.5-flash", "Gemini 3.5 Flash (Standart)"),
        ("gemini-3.7-flash", "Gemini 3.7 Flash (Yangi)"),
        ("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite (Tez)"),
        ("gemini-3.6-flash", "Gemini 3.6 Flash"),
    ]

    buttons = []
    for model_id, label in models:
        prefix = "✅ " if current_model == model_id else "🔹 "
        buttons.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=f"adm:set_model:{model_id}")])

    # Temperature presets
    temp_row = []
    temps = [(0.1, "🎯 0.1 Aniq"), (0.3, "⚖️ 0.3 Muvozanat"), (0.7, "🎨 0.7 Ijodiy")]
    for t_val, t_label in temps:
        t_prefix = "✅ " if abs(current_temp - t_val) < 0.05 else ""
        temp_row.append(InlineKeyboardButton(text=f"{t_prefix}{t_label}", callback_data=f"adm:set_temp:{t_val}"))
    buttons.append(temp_row)

    buttons.append([InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_broadcast_setup_keyboard(has_button: bool = False) -> InlineKeyboardMarkup:
    """Interactive broadcast composer keyboard."""
    buttons = []
    if not has_button:
        buttons.append([InlineKeyboardButton(text="➕ Tugma (URL Link) Qo'shish", callback_data="adm:bc_add_btn")])
    else:
        buttons.append([InlineKeyboardButton(text="🗑 Tugmani O'chirish", callback_data="adm:bc_rm_btn")])

    buttons.append([
        InlineKeyboardButton(text="👁 O'zimga Sinov Yuborish (Test)", callback_data="adm:bc_test_send"),
        InlineKeyboardButton(text="🚀 Barchaga Tarqatish", callback_data="adm:confirm_broadcast")
    ])
    buttons.append([InlineKeyboardButton(text="❌ Bekor Qilish", callback_data="adm:cancel_broadcast")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
