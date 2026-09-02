import html
import logging
from typing import List
from aiogram import Router, F
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from bot.services.tmdb_service import tmdb_service

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def handle_inline_movie_search(inline_query: InlineQuery):
    """
    Handles live inline queries like: `@FilmAiFinderbot Inception`.
    Allows searching movies directly from any Telegram group or chat.
    """
    query = inline_query.query.strip()
    if not query or len(query) < 2:
        # Prompt hint
        hint_article = InlineQueryResultArticle(
            id="hint",
            title="🎬 Qidirish uchun kino nomini yozing...",
            description="Masalan: @FilmAiFinderbot Avatar yoki @FilmAiFinderbot Qasoskorlar",
            thumbnail_url="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=200",
            input_message_content=InputTextMessageContent(
                message_text="🎬 <b>AI FilmFinder</b> orqali istalgan filmni qidiring: @FilmAiFinderbot",
                parse_mode="HTML"
            )
        )
        await inline_query.answer([hint_article], cache_time=5, is_personal=True)
        return

    results: List[InlineQueryResultArticle] = []

    try:
        # Search via TMDb
        media_info = await tmdb_service.search_media(query)
        if media_info and media_info.get("title"):
            title = media_info.get("title", query)
            year = media_info.get("release_year", "")
            overview = media_info.get("overview", "")[:180] + "..." if media_info.get("overview") else "Syujet mavjud emas."
            rating = media_info.get("rating", "8.0")
            poster = media_info.get("poster_url") or "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400"
            yt_trailer = media_info.get("trailer_url") or f"https://www.youtube.com/results?search_query={html.escape(title)}+treyler"
            kinopoisk_url = f"https://www.google.com/search?q={html.escape(title)}+kinopoisk"

            msg_text = (
                f"🎬 <b>{html.escape(title)} ({year})</b>\n"
                f"⭐️ <b>Reyting:</b> {rating} / 10\n\n"
                f"📖 <b>Syujet:</b>\n{html.escape(overview)}\n\n"
                f"🤖 <i>Topildi: @FilmAiFinderbot</i>"
            )

            buttons = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🍿 Treyler Ko'rish", url=yt_trailer),
                    InlineKeyboardButton(text="⭐️ Kinopoisk", url=kinopoisk_url)
                ],
                [
                    InlineKeyboardButton(text="🔍 Boshqa Kino Qidirish", url="https://t.me/FilmAiFinderbot")
                ]
            ])

            results.append(InlineQueryResultArticle(
                id="tmdb_1",
                title=f"{title} ({year})",
                description=f"⭐️ {rating} | {overview[:80]}...",
                thumbnail_url=poster,
                input_message_content=InputTextMessageContent(
                    message_text=msg_text,
                    parse_mode="HTML"
                ),
                reply_markup=buttons
            ))
    except Exception as e:
        logger.warning(f"[Inline Search Error] {e}")

    # Fallback generic result if nothing found
    if not results:
        results.append(InlineQueryResultArticle(
            id="fallback_search",
            title=f"🔍 '{query}' bo'yicha qidiruv",
            description="Ushbu filmni @FilmAiFinderbot orqali topish",
            thumbnail_url="https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=200",
            input_message_content=InputTextMessageContent(
                message_text=f"🎬 <b>{html.escape(query)}</b> filmini @FilmAiFinderbot orqali qidirmoqdaman!",
                parse_mode="HTML"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎬 Botga Kirish", url=f"https://t.me/FilmAiFinderbot?start=search")]
            ])
        ))

    await inline_query.answer(results, cache_time=10, is_personal=True)
