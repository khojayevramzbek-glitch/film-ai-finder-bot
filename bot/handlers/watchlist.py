import html
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.services.db import (
    get_user_lang,
    add_to_watchlist,
    remove_from_watchlist,
    get_user_watchlist,
    add_premiere_alert,
    get_user_premiere_alerts
)
from bot.locales import get_msg
from bot.keyboards.inline import get_saved_item_keyboard

router = Router()


async def safe_answer(callback: CallbackQuery, text: str = "", show_alert: bool = False):
    try:
        if text:
            await callback.answer(text, show_alert=show_alert)
        else:
            await callback.answer()
    except Exception:
        pass


@router.message(Command("saved"))
@router.message(Command("watchlist"))
async def cmd_saved_movies(message: Message):
    """Displays user's saved movies watchlist."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    saved_list = get_user_watchlist(user_id, limit=15)
    if not saved_list:
        await message.answer(get_msg(lang, "watchlist_empty"), parse_mode="HTML")
        return

    lines = [get_msg(lang, "watchlist_title")]
    for idx, item in enumerate(saved_list, 1):
        m_title = html.escape(str(item.get("movie_title", "")))
        m_year = html.escape(str(item.get("release_year", "")))
        year_str = f" ({m_year})" if m_year else ""
        lines.append(f"<b>{idx}. {m_title}</b>{year_str}")

    lines.append("\n💡 <i>Biror filmni tomosha qilish yoki o'chirish uchun pastdagi tugmalardan foydalaning.</i>")

    # Send first 5 interactive action buttons
    buttons = []
    for item in saved_list[:5]:
        m_title = item.get("movie_title", "")
        buttons.append([
            InlineKeyboardButton(text=f"🎬 {m_title[:25]}", callback_data=f"show_save:{m_title[:20]}")
        ])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
    await message.answer("\n".join(lines), reply_markup=reply_markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("show_save:"))
async def cb_show_saved_item(callback: CallbackQuery):
    """Shows details for a saved item."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    title = callback.data.split(":", 1)[1]

    text = f"🎬 <b>{html.escape(title)}</b>\n\nQuyidagi tugmalar orqali tomosha qiling yoki ro'yxatdan o'chiring:"
    await callback.message.reply(text, reply_markup=get_saved_item_keyboard(title, lang=lang), parse_mode="HTML")
    await safe_answer(callback)


@router.callback_query(F.data.startswith("save:"))
async def cb_save_movie(callback: CallbackQuery):
    """Adds movie to watchlist."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    title = callback.data.split(":", 1)[1]

    add_to_watchlist(user_id=user_id, movie_title=title)
    await safe_answer(callback, "❤️ Film saqlanganlar ro'yxatiga qo'shildi! (/saved)", show_alert=False)


@router.callback_query(F.data.startswith("unsave:"))
async def cb_unsave_movie(callback: CallbackQuery):
    """Removes movie from watchlist."""
    user_id = callback.from_user.id if callback.from_user else 0
    title = callback.data.split(":", 1)[1]

    remove_from_watchlist(user_id=user_id, movie_title=title)
    await safe_answer(callback, "🗑 Film saqlanganlar ro'yxatidan o'chirildi.", show_alert=False)
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.message(Command("alerts"))
async def cmd_premiere_alerts(message: Message):
    """Displays user's premiere alerts."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    alerts = get_user_premiere_alerts(user_id)
    if not alerts:
        await message.answer(get_msg(lang, "alerts_empty"), parse_mode="HTML")
        return

    lines = [get_msg(lang, "alerts_title")]
    for idx, item in enumerate(alerts, 1):
        m_title = html.escape(str(item.get("movie_title", "")))
        p_date = html.escape(str(item.get("premiere_date", "")))
        date_str = f" <i>(Premyera: {p_date})</i>" if p_date else ""
        lines.append(f"<b>{idx}. {m_title}</b>{date_str}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data.startswith("alert:"))
async def cb_set_alert(callback: CallbackQuery):
    """Subscribes to premiere alert."""
    user_id = callback.from_user.id if callback.from_user else 0
    title = callback.data.split(":", 1)[1]

    add_premiere_alert(user_id=user_id, movie_title=title)
    await safe_answer(callback, "🔔 Premyera kuni sizga maxsus eslatma yuboriladi! (/alerts)", show_alert=True)
