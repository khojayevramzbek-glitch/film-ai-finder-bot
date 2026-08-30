import urllib.parse
from typing import Optional, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.locales import get_msg


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Returns interactive language selection buttons."""
    buttons = [
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha (Lotin)", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇺🇿 Ўзбекча (Кирилл)", callback_data="lang:uz_kr"),
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_movie_keyboard(ai_data: Dict[str, Any], tmdb_data: Optional[Dict[str, Any]] = None, lang: str = "uz") -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard with localized trailer, search, and share buttons.
    """
    buttons = []

    title = ai_data.get("title_original") or (tmdb_data.get("title") if tmdb_data else "") or ""
    encoded_title = urllib.parse.quote(title)

    # 1. Trailer Button
    trailer_url = tmdb_data.get("trailer_url") if tmdb_data else None
    if trailer_url:
        buttons.append([
            InlineKeyboardButton(text=get_msg(lang, "btn_trailer"), url=trailer_url)
        ])
    else:
        yt_search_url = f"https://www.youtube.com/results?search_query={encoded_title}+trailer"
        buttons.append([
            InlineKeyboardButton(text=get_msg(lang, "btn_trailer_search"), url=yt_search_url)
        ])

    row2 = []
    # 2. IMDb / Kinopoisk
    imdb_id = tmdb_data.get("imdb_id") if tmdb_data else None
    if imdb_id:
        row2.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_imdb"), url=f"https://www.imdb.com/title/{imdb_id}/")
        )
    else:
        kinopoisk_url = f"https://www.kinopoisk.ru/index.php?kp_query={encoded_title}"
        row2.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_kinopoisk"), url=kinopoisk_url)
        )

    # 3. TMDb / Google Search
    tmdb_url = tmdb_data.get("tmdb_url") if tmdb_data else None
    if tmdb_url:
        row2.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_tmdb"), url=tmdb_url)
        )
    else:
        google_url = f"https://www.google.com/search?q={encoded_title}+movie"
        row2.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_google"), url=google_url)
        )

    if row2:
        buttons.append(row2)

    # 4. Share button
    share_template = get_msg(lang, "share_text", title=title)
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(share_template)}"
    buttons.append([
        InlineKeyboardButton(text=get_msg(lang, "btn_share"), url=share_url)
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
