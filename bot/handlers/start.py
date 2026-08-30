from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.services.db import get_user_lang, set_user_lang
from bot.locales import get_msg
from bot.keyboards.inline import get_language_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handles /start command with language prompt for new users."""
    user_id = message.from_user.id if message.from_user else 0
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    current_lang = get_user_lang(user_id)

    if not current_lang:
        # First time user -> Show language selection keyboard
        text = get_msg("uz", "choose_lang")
        await message.answer(text, reply_markup=get_language_keyboard(), parse_mode="HTML")
        return

    # Existing user -> Show welcome message in their language
    text = get_msg(current_lang, "welcome", name=user_name)
    change_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_msg(current_lang, "btn_change_lang"), callback_data="change_lang")]
    ])
    await message.answer(text, reply_markup=change_btn, parse_mode="HTML")


@router.message(Command("lang"))
@router.message(Command("language"))
async def cmd_language(message: Message):
    """Allows user to change language anytime."""
    user_id = message.from_user.id if message.from_user else 0
    current_lang = get_user_lang(user_id) or "uz"
    text = get_msg(current_lang, "choose_lang")
    await message.answer(text, reply_markup=get_language_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "change_lang")
async def cb_change_lang(callback: CallbackQuery):
    """Handles inline button to change language."""
    user_id = callback.from_user.id if callback.from_user else 0
    current_lang = get_user_lang(user_id) or "uz"
    text = get_msg(current_lang, "choose_lang")
    await callback.message.edit_text(text, reply_markup=get_language_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(callback: CallbackQuery):
    """Saves user's language selection and shows welcome message."""
    user_id = callback.from_user.id if callback.from_user else 0
    user_name = callback.from_user.first_name if callback.from_user else "Foydalanuvchi"
    
    selected_lang = callback.data.split(":")[1]
    set_user_lang(user_id, selected_lang)

    welcome_text = get_msg(selected_lang, "welcome", name=user_name)
    change_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_msg(selected_lang, "btn_change_lang"), callback_data="change_lang")]
    ])

    await callback.message.edit_text(welcome_text, reply_markup=change_btn, parse_mode="HTML")
    await callback.answer(get_msg(selected_lang, "lang_changed"), show_alert=False)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handles /help command in user's preferred language."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    text = get_msg(lang, "help")
    contact_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_msg(lang, "btn_contact_admin"), url="https://t.me/khojayev_ramz")]
    ])
    await message.answer(text, reply_markup=contact_btn, parse_mode="HTML")


@router.message(Command("about"))
async def cmd_about(message: Message):
    """Handles /about command in user's preferred language."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    text = get_msg(lang, "about")
    contact_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_msg(lang, "btn_contact_admin"), url="https://t.me/khojayev_ramz")]
    ])
    await message.answer(text, reply_markup=contact_btn, parse_mode="HTML")
