from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Main Control Panel Dashboard keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Jonli Statistika", callback_data="adm:stats"),
            InlineKeyboardButton(text="🔑 API Kalitlar Holati", callback_data="adm:keys"),
        ],
        [
            InlineKeyboardButton(text="📢 Xabar Tarqatish", callback_data="adm:broadcast"),
            InlineKeyboardButton(text="📢 Homiy Kanallar", callback_data="adm:channels"),
        ],
        [
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users"),
            InlineKeyboardButton(text="📥 Baza Faylini Yuklash", callback_data="adm:export_db"),
        ],
        [
            InlineKeyboardButton(text="🔄 Kalitlarni Tiklash", callback_data="adm:reset_keys"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Back to main admin menu button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Boshqaruv Paneliga Qaytish", callback_data="adm:menu")]
    ])


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation buttons for broadcast message."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Xabarni Barchaga Yuborish", callback_data="adm:confirm_broadcast"),
            InlineKeyboardButton(text="❌ Bekor Qilish", callback_data="adm:cancel_broadcast"),
        ]
    ])
