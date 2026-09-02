import html
import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction

from bot.services.db import get_user_lang, set_user_lang
from bot.locales import get_msg
from bot.keyboards.inline import get_language_keyboard, get_genres_keyboard, get_random_movie_keyboard
from bot.services.ai_service import ai_service
from bot.services.tmdb_service import tmdb_service

logger = logging.getLogger(__name__)
router = Router()


async def safe_answer_cb(callback: CallbackQuery, text: str = "", show_alert: bool = False):
    """Safely acknowledges callback queries without throwing expired query errors."""
    try:
        if text:
            await callback.answer(text, show_alert=show_alert)
        else:
            await callback.answer()
    except Exception:
        pass


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handles /start command with language prompt for new users and referral processing."""
    user_id = message.from_user.id if message.from_user else 0
    user_name = message.from_user.first_name if message.from_user else "Foydalanuvchi"
    current_lang = get_user_lang(user_id)

    # Process referral invitation
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref_id_str = parts[1].replace("ref_", "").strip()
        if ref_id_str.isdigit():
            from bot.services.db import add_referral
            add_referral(new_user_id=user_id, referrer_id=int(ref_id_str))

    if not current_lang:
        # First time user -> Show language selection keyboard
        text = get_msg("uz", "choose_lang")
        await message.answer(text, reply_markup=get_language_keyboard(), parse_mode="HTML")
        return

    # Existing user -> Show welcome message in their language
    text = get_msg(current_lang, "welcome", name=html.escape(user_name))
    menu_btns = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_msg(current_lang, "btn_random_more"), callback_data="rand_menu"),
            InlineKeyboardButton(text="❤️ Saqlanganlar", callback_data="btn_saved")
        ],
        [
            InlineKeyboardButton(text="📂 Tarix (/history)", callback_data="btn_history"),
            InlineKeyboardButton(text="👥 Taklif Qilish (/invite)", callback_data="btn_invite")
        ],
        [
            InlineKeyboardButton(text=get_msg(current_lang, "btn_change_lang"), callback_data="change_lang")
        ]
    ])
    await message.answer(text, reply_markup=menu_btns, parse_mode="HTML")


@router.message(Command("random"))
async def cmd_random(message: Message):
    """Handles /random command to choose movie by genre."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    text = get_msg(lang, "random_choose_genre")
    await message.answer(text, reply_markup=get_genres_keyboard(lang), parse_mode="HTML")


@router.callback_query(F.data == "rand_menu")
async def cb_random_menu(callback: CallbackQuery):
    """Shows genres list again."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    text = get_msg(lang, "random_choose_genre")
    try:
        await callback.message.edit_text(text, reply_markup=get_genres_keyboard(lang), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_genres_keyboard(lang), parse_mode="HTML")
    await safe_answer_cb(callback)


@router.callback_query(F.data.startswith("rand_genre:"))
async def cb_pick_random_genre(callback: CallbackQuery, bot: Bot):
    """Fetches a high-rated unique movie from selected genre, excluding previously recommended title."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    # Extract genre and optional exclusion title from callback data
    parts = callback.data.split(":")
    genre_key = parts[1]
    exclude_title = parts[2] if len(parts) > 2 else ""

    genre_name = get_msg(lang, f"genre_{genre_key}")
    await safe_answer_cb(callback, f"🎲 {genre_name}...")

    try:
        status_msg = await callback.message.edit_text(
            f"🎲 <b>{html.escape(genre_name)}</b> janridagi yangi sara film tanlanmoqda...",
            parse_mode="HTML"
        )
    except Exception:
        status_msg = callback.message

    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)

    # Fetch with exclusion
    movie = await ai_service.get_random_movie(genre_name, exclude_title=exclude_title, lang=lang)

    if not movie or not movie.get("title_original"):
        try:
            await status_msg.edit_text("❌ Film tanlashda xatolik yuz berdi. Qayta urinib ko'ring.", parse_mode="HTML")
        except Exception:
            pass
        return

    title_orig = html.escape(str(movie.get("title_original", "")))
    title_local = html.escape(str(movie.get("title_local", "")))
    year = html.escape(str(movie.get("release_year", "")))
    rating = html.escape(str(movie.get("rating", "")))
    summary = html.escape(str(movie.get("summary", "")))
    why_watch = html.escape(str(movie.get("why_watch", "")))

    lines = [
        f"🎬 <b>{title_orig}</b> ({year})",
    ]
    if title_local and title_local.lower() != title_orig.lower():
        lines.append(f"📌 <i>{title_local}</i>")

    lines.append("")
    if rating:
        lines.append(f"⭐ <b>Reyting:</b> {rating}/10")
    lines.append(f"🎭 <b>Janr:</b> {html.escape(genre_name)}")

    if summary:
        lines.append("")
        lines.append(f"📖 <b>Mazmuni:</b>\n{summary}")

    if why_watch:
        lines.append("")
        lines.append(f"💡 <b>Nima uchun ko'rish kerak:</b>\n<i>{why_watch}</i>")

    reply_markup = get_random_movie_keyboard(title=title_orig, genre_key=genre_key, lang=lang)

    # Try fetching poster from TMDb
    tmdb_info = await tmdb_service.search_media(title_orig, year=year)
    poster_url = tmdb_info.get("poster_url") if tmdb_info else None

    if poster_url:
        try:
            await status_msg.delete()
            await callback.message.answer_photo(
                photo=poster_url,
                caption="\n".join(lines)[:1000],
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    try:
        await status_msg.edit_text("\n".join(lines), reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=reply_markup, parse_mode="HTML")


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
    try:
        await callback.message.edit_text(text, reply_markup=get_language_keyboard(), parse_mode="HTML")
    except Exception:
        pass
    await safe_answer_cb(callback)


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(callback: CallbackQuery):
    """Saves user's language selection and shows welcome message."""
    user_id = callback.from_user.id if callback.from_user else 0
    user_name = callback.from_user.first_name if callback.from_user else "Foydalanuvchi"
    user_handle = callback.from_user.username or ""
    
    is_new = get_user_lang(user_id) is None
    selected_lang = callback.data.split(":")[1]
    set_user_lang(user_id, selected_lang, username=user_handle, first_name=user_name)

    # Live Admin Alert if newly registered
    if is_new:
        from bot.config import ADMIN_BOT_TOKEN
        from bot.services.db import get_admin_setting
        if ADMIN_BOT_TOKEN and get_admin_setting("live_alerts_enabled", "1") == "1":
            admin_chat_id = get_admin_setting("admin_chat_id", "")
            if admin_chat_id:
                asyncio.create_task(_send_admin_new_user_alert(
                    admin_chat_id=int(admin_chat_id),
                    user_id=user_id,
                    user_name=user_name,
                    user_handle=user_handle,
                    lang=selected_lang
                ))

    welcome_text = get_msg(selected_lang, "welcome", name=html.escape(user_name))
    menu_btns = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_msg(selected_lang, "btn_random_more"), callback_data="rand_menu"),
            InlineKeyboardButton(text=get_msg(selected_lang, "btn_change_lang"), callback_data="change_lang")
        ]
    ])

    try:
        await callback.message.edit_text(welcome_text, reply_markup=menu_btns, parse_mode="HTML")
    except Exception:
        await callback.message.answer(welcome_text, reply_markup=menu_btns, parse_mode="HTML")
    await safe_answer_cb(callback, get_msg(selected_lang, "lang_changed"), show_alert=False)


async def _send_admin_new_user_alert(admin_chat_id: int, user_id: int, user_name: str, user_handle: str, lang: str):
    """Discreet real-time notification to admin bot."""
    from bot.config import ADMIN_BOT_TOKEN
    from aiogram import Bot as AlertBot
    alert_bot = None
    try:
        alert_bot = AlertBot(token=ADMIN_BOT_TOKEN)
        u_link = f"@{user_handle}" if user_handle else "<i>Mavjud emas</i>"
        alert_text = (
            "🔔 <b>YANGI FOYDALANUVCHI QO'SHILDI!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Ismi:</b> {html.escape(user_name)}\n"
            f"🔗 <b>Username:</b> {u_link}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"🌐 <b>Tili:</b> {lang.upper()}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        )
        await alert_bot.send_message(chat_id=admin_chat_id, text=alert_text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"[Live Alert Failed] {e}")
    finally:
        if alert_bot:
            await alert_bot.session.close()


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
