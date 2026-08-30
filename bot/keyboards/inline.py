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


def safe_callback_data(prefix: str, data: str, max_bytes: int = 64) -> str:
    """Ensures callback_data does not exceed Telegram's strict 64-byte limit."""
    prefix_bytes_len = len(prefix.encode('utf-8'))
    allowed_len = max_bytes - prefix_bytes_len
    encoded = data.encode('utf-8')[:allowed_len]
    return f"{prefix}{encoded.decode('utf-8', errors='ignore')}"


def get_movie_keyboard(ai_data: Dict[str, Any], tmdb_data: Optional[Dict[str, Any]] = None, lang: str = "uz") -> InlineKeyboardMarkup:
    """
    Creates rich movie action buttons: Trailer, Watch Uzbek, Similar Movies, IMDb, Share.
    Safely enforces Telegram 64-byte callback_data limits.
    """
    buttons = []

    title = str(ai_data.get("title_original") or (tmdb_data.get("title") if tmdb_data else "") or "Movie")
    encoded_title = urllib.parse.quote(title)

    # 1. Trailer & Watch Online in Uzbek
    row1 = []
    trailer_url = tmdb_data.get("trailer_url") if tmdb_data else None
    if trailer_url:
        row1.append(InlineKeyboardButton(text=get_msg(lang, "btn_trailer"), url=trailer_url))
    else:
        yt_search_url = f"https://www.youtube.com/results?search_query={encoded_title}+trailer"
        row1.append(InlineKeyboardButton(text=get_msg(lang, "btn_trailer_search"), url=yt_search_url))

    watch_uz_url = f"https://www.google.com/search?q={encoded_title}+tarjima+kino+uzbek+tilida+skachat+korish"
    row1.append(InlineKeyboardButton(text=get_msg(lang, "btn_watch_uz"), url=watch_uz_url))
    buttons.append(row1)

    # 2. Similar Movies (Safe 64-byte callback data)
    cb_data = safe_callback_data("sim:", title)
    buttons.append([
        InlineKeyboardButton(text=get_msg(lang, "btn_similar"), callback_data=cb_data)
    ])

    # 3. IMDb / Kinopoisk / TMDb
    row3 = []
    imdb_id = tmdb_data.get("imdb_id") if tmdb_data else None
    if imdb_id:
        row3.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_imdb"), url=f"https://www.imdb.com/title/{imdb_id}/")
        )
    else:
        kinopoisk_url = f"https://www.kinopoisk.ru/index.php?kp_query={encoded_title}"
        row3.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_kinopoisk"), url=kinopoisk_url)
        )

    tmdb_url = tmdb_data.get("tmdb_url") if tmdb_data else None
    if tmdb_url:
        row3.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_tmdb"), url=tmdb_url)
        )
    else:
        google_url = f"https://www.google.com/search?q={encoded_title}+movie"
        row3.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_google"), url=google_url)
        )
    buttons.append(row3)

    # 4. Share button
    share_template = get_msg(lang, "share_text", title=title)
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(share_template)}"
    buttons.append([
        InlineKeyboardButton(text=get_msg(lang, "btn_share"), url=share_url)
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_genres_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Returns interactive genre buttons for /random movie picker."""
    buttons = [
        [
            InlineKeyboardButton(text=get_msg(lang, "genre_action"), callback_data="rand_genre:action"),
            InlineKeyboardButton(text=get_msg(lang, "genre_comedy"), callback_data="rand_genre:comedy"),
        ],
        [
            InlineKeyboardButton(text=get_msg(lang, "genre_scifi"), callback_data="rand_genre:scifi"),
            InlineKeyboardButton(text=get_msg(lang, "genre_horror"), callback_data="rand_genre:horror"),
        ],
        [
            InlineKeyboardButton(text=get_msg(lang, "genre_drama"), callback_data="rand_genre:drama"),
            InlineKeyboardButton(text=get_msg(lang, "genre_cartoon"), callback_data="rand_genre:cartoon"),
        ],
        [
            InlineKeyboardButton(text=get_msg(lang, "genre_anime"), callback_data="rand_genre:anime"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_random_movie_keyboard(title: str, genre_key: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Buttons for recommended random movie."""
    encoded_title = urllib.parse.quote(title)
    yt_url = f"https://www.youtube.com/results?search_query={encoded_title}+trailer"
    watch_url = f"https://www.google.com/search?q={encoded_title}+tarjima+kino+uzbek+tilida+skachat+korish"

    buttons = [
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_trailer_search"), url=yt_url),
            InlineKeyboardButton(text=get_msg(lang, "btn_watch_uz"), url=watch_url),
        ],
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_random_more"), callback_data=f"rand_genre:{genre_key}"),
            InlineKeyboardButton(text=get_msg(lang, "btn_back_genres"), callback_data="rand_menu"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
