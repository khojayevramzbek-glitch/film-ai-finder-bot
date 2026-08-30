import urllib.parse
from typing import Optional, Dict, Any, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.locales import get_msg


def safe_callback_data(prefix: str, data: str, max_bytes: int = 64) -> str:
    """Ensures callback_data does not exceed Telegram's strict 64-byte limit."""
    prefix_bytes_len = len(prefix.encode('utf-8'))
    allowed_len = max_bytes - prefix_bytes_len
    encoded = data.encode('utf-8')[:allowed_len]
    return f"{prefix}{encoded.decode('utf-8', errors='ignore')}"


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


def get_movie_keyboard(
    ai_data: Dict[str, Any],
    tmdb_data: Optional[Dict[str, Any]] = None,
    is_saved: bool = False,
    is_alert_set: bool = False,
    lang: str = "uz"
) -> InlineKeyboardMarkup:
    """
    Creates rich movie action buttons: Trailer, Watch Online, Save Watchlist, Premiere Alert, Similar Movies, IMDb, Share.
    """
    buttons = []

    title = str(ai_data.get("title_original") or (tmdb_data.get("title") if tmdb_data else "") or "Movie")
    encoded_title = urllib.parse.quote(title)
    clean_title = title.replace(":", " ").strip()[:20]

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

    # 2. Save Watchlist (❤️) & Premiere Alert (🔔)
    row2 = []
    save_text = get_msg(lang, "btn_saved_done") if is_saved else get_msg(lang, "btn_save_movie")
    save_cb = safe_callback_data("unsave:" if is_saved else "save:", clean_title)
    row2.append(InlineKeyboardButton(text=save_text, callback_data=save_cb))

    is_premiere = ai_data.get("is_premiere", False) or (tmdb_data.get("is_premiere", False) if tmdb_data else False)
    if is_premiere:
        alert_text = get_msg(lang, "btn_alert_done") if is_alert_set else get_msg(lang, "btn_premiere_alert")
        alert_cb = safe_callback_data("unalert:" if is_alert_set else "alert:", clean_title)
        row2.append(InlineKeyboardButton(text=alert_text, callback_data=alert_cb))

    buttons.append(row2)

    # 3. Similar Movies (AI recommendation)
    sim_cb = safe_callback_data("sim:", clean_title)
    buttons.append([
        InlineKeyboardButton(text=get_msg(lang, "btn_similar"), callback_data=sim_cb)
    ])

    # 4. IMDb / Kinopoisk / TMDb
    row4 = []
    imdb_id = tmdb_data.get("imdb_id") if tmdb_data else None
    if imdb_id:
        row4.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_imdb"), url=f"https://www.imdb.com/title/{imdb_id}/")
        )
    else:
        kinopoisk_url = f"https://www.kinopoisk.ru/index.php?kp_query={encoded_title}"
        row4.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_kinopoisk"), url=kinopoisk_url)
        )

    tmdb_url = tmdb_data.get("tmdb_url") if tmdb_data else None
    if tmdb_url:
        row4.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_tmdb"), url=tmdb_url)
        )
    else:
        google_url = f"https://www.google.com/search?q={encoded_title}+movie"
        row4.append(
            InlineKeyboardButton(text=get_msg(lang, "btn_google"), url=google_url)
        )
    buttons.append(row4)

    # 5. Share button
    share_template = get_msg(lang, "share_text", title=title)
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(share_template)}"
    buttons.append([
        InlineKeyboardButton(text=get_msg(lang, "btn_share"), url=share_url)
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_genres_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Returns interactive genre buttons for /random AI movie picker."""
    buttons = [
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_surprise_me"), callback_data="rand_genre:surprise"),
        ],
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
            InlineKeyboardButton(text=get_msg(lang, "genre_thriller"), callback_data="rand_genre:thriller"),
            InlineKeyboardButton(text=get_msg(lang, "genre_romance"), callback_data="rand_genre:romance"),
        ],
        [
            InlineKeyboardButton(text=get_msg(lang, "genre_anime"), callback_data="rand_genre:anime"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_random_movie_keyboard(title: str, genre_key: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Buttons for recommended random movie with safe exclusion callback data."""
    encoded_title = urllib.parse.quote(title)
    yt_url = f"https://www.youtube.com/results?search_query={encoded_title}+trailer"
    watch_url = f"https://www.google.com/search?q={encoded_title}+tarjima+kino+uzbek+tilida+skachat+korish"

    clean_title = title.replace(":", " ").strip()[:20]
    next_cb = safe_callback_data(f"rand_genre:{genre_key}:", clean_title)
    save_cb = safe_callback_data("save:", clean_title)

    buttons = [
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_trailer_search"), url=yt_url),
            InlineKeyboardButton(text=get_msg(lang, "btn_watch_uz"), url=watch_url),
        ],
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_save_movie"), callback_data=save_cb),
            InlineKeyboardButton(text=get_msg(lang, "btn_random_more"), callback_data=next_cb),
        ],
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_back_genres"), callback_data="rand_menu"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiz_keyboard(options: List[str], correct_idx: int) -> InlineKeyboardMarkup:
    """Generates 4 option buttons for the Movie Quiz."""
    labels = ["A", "B", "C", "D"]
    buttons = []
    for idx, opt in enumerate(options[:4]):
        btn_text = f"{labels[idx]}) {opt[:35]}"
        cb = f"quiz_ans:{idx}:{correct_idx}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_quiz_result_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    """Next question and leaderboard buttons."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_next_quiz"), callback_data="quiz_next"),
            InlineKeyboardButton(text=get_msg(lang, "btn_leaderboard"), callback_data="quiz_top"),
        ]
    ])


def get_saved_item_keyboard(movie_title: str, lang: str = "uz") -> InlineKeyboardMarkup:
    """Actions for an individual saved movie in Watchlist."""
    encoded_title = urllib.parse.quote(movie_title)
    watch_url = f"https://www.google.com/search?q={encoded_title}+tarjima+kino+uzbek+tilida+skachat+korish"
    clean_title = movie_title.replace(":", " ").strip()[:20]
    unsave_cb = safe_callback_data("unsave:", clean_title)

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_msg(lang, "btn_watch_uz"), url=watch_url),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=unsave_cb)
        ]
    ])
