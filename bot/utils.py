import re
import html
from pathlib import Path
from typing import Optional, Dict, Any, List
from bot.locales import get_msg

# Regex to detect URLs in message
URL_REGEX = re.compile(
    r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|'
    r'https?:\/\/(?:www\.)?[a-zA-Z0-9]+\.[^\s]{2,})',
    re.IGNORECASE
)

# Supported popular platform domains
SUPPORTED_DOMAINS = [
    "instagram.com",
    "instagr.am",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "pin.it",
    "facebook.com",
    "fb.watch",
    "twitter.com",
    "x.com",
    "threads.net"
]


def extract_urls(text: str) -> List[str]:
    """Extracts all valid URLs from the input text."""
    if not text:
        return []
    matches = URL_REGEX.findall(text)
    cleaned = []
    for url in matches:
        url = url.strip().rstrip(".,!?:;)\"'>")
        if url:
            cleaned.append(url)
    return cleaned


def is_supported_url(url: str) -> bool:
    """Checks if the URL is from one of the supported media platforms."""
    lower_url = url.lower()
    return any(domain in lower_url for domain in SUPPORTED_DOMAINS)


def safe_remove(path: Optional[Path | str]) -> None:
    """Safely removes a file if it exists."""
    if not path:
        return
    try:
        p = Path(path)
        if p.exists() and p.is_file():
            p.unlink()
    except Exception as e:
        print(f"[Warning] Faylni o'chirishda xatolik: {e}")


def get_media_type_badge(media_type: str, lang: str = "uz") -> str:
    """Returns localized badge for media type."""
    m_type = (media_type or "").lower()
    if "movie" in m_type or "film" in m_type or "kino" in m_type:
        return get_msg(lang, "type_movie")
    elif "series" in m_type or "serial" in m_type or "tv" in m_type or "drama" in m_type or "dorama" in m_type:
        return get_msg(lang, "type_series")
    elif "cartoon" in m_type or "multfilm" in m_type or "animatsiya" in m_type:
        return get_msg(lang, "type_cartoon")
    elif "anime" in m_type:
        return get_msg(lang, "type_anime")
    elif "trailer" in m_type or "treyler" in m_type:
        return get_msg(lang, "type_trailer")
    return get_msg(lang, "type_movie")


def format_movie_response(ai_data: Dict[str, Any], tmdb_data: Optional[Dict[str, Any]] = None, lang: str = "uz", max_len: int = 1000) -> str:
    """
    Formats AI and TMDb data into a rich Telegram HTML message in user's preferred language.
    Guarantees that length does not exceed max_len (Telegram photo caption limit is 1024).
    """
    title_orig = ai_data.get("title_original") or (tmdb_data.get("title") if tmdb_data else None) or "Unknown"
    title_uz = ai_data.get("title_uz") or ""
    title_ru = ai_data.get("title_ru") or (tmdb_data.get("title_ru") if tmdb_data else "")

    media_type = ai_data.get("media_type") or (tmdb_data.get("media_type") if tmdb_data else "movie")
    media_badge = get_media_type_badge(media_type, lang=lang)

    # Premiere / Release Status
    is_premiere = ai_data.get("is_premiere", False) or (tmdb_data.get("is_premiere", False) if tmdb_data else False)
    release_year = ai_data.get("release_year") or (tmdb_data.get("year") if tmdb_data else "")
    premiere_date = ai_data.get("premiere_date") or (tmdb_data.get("release_date") if tmdb_data else "")

    # Rating & Genres from TMDb if available
    rating = tmdb_data.get("rating") if tmdb_data else None
    genres = tmdb_data.get("genres") if tmdb_data else []

    # Actors / Characters
    actors = ai_data.get("characters_or_actors") or (tmdb_data.get("cast") if tmdb_data else [])

    # Overview / Plot
    summary = str(ai_data.get("summary") or (tmdb_data.get("overview") if tmdb_data else "") or "").strip()
    scene_desc = str(ai_data.get("scene_description") or "").strip()

    # Build HTML Message
    lines = []

    # Title header
    lines.append(f"✨ <b>{html.escape(str(title_orig))}</b>")
    
    # Secondary titles
    if lang in ["uz", "uz_kr"] and title_uz and title_uz.lower() != str(title_orig).lower():
        lines.append(f"🇺🇿 <i>{html.escape(str(title_uz))}</i>")
    if lang == "ru" and title_ru and title_ru.lower() != str(title_orig).lower():
        lines.append(f"🇷🇺 <i>{html.escape(str(title_ru))}</i>")
    elif lang in ["uz", "uz_kr"] and title_ru and title_ru.lower() != str(title_orig).lower() and title_ru.lower() != str(title_uz).lower():
        lines.append(f"🇷🇺 <i>{html.escape(str(title_ru))}</i>")

    lines.append("")
    lines.append(f"{get_msg(lang, 'label_type')} {media_badge}")

    # Premiere or Release Year
    if is_premiere:
        date_str = f" ({html.escape(str(premiere_date))})" if premiere_date else ""
        lines.append(f"{get_msg(lang, 'label_premiere')}{date_str}")
    elif release_year:
        lines.append(f"{get_msg(lang, 'label_year')} {html.escape(str(release_year))}")

    # Rating
    if rating:
        lines.append(f"{get_msg(lang, 'label_rating')} {rating}/10")

    # Genres
    if genres and isinstance(genres, list):
        genre_str = ", ".join([html.escape(str(g)) for g in genres[:4] if g])
        if genre_str:
            lines.append(f"{get_msg(lang, 'label_genres')} {genre_str}")

    # Actors
    if actors:
        actor_list = actors[:4] if isinstance(actors, list) else [str(actors)]
        actor_str = ", ".join([html.escape(str(a)) for a in actor_list if a])
        if actor_str:
            lines.append(f"{get_msg(lang, 'label_actors')} {actor_str}")

    # Scene context
    if scene_desc:
        lines.append("")
        lines.append(f"{get_msg(lang, 'label_scene')}\n<i>{html.escape(scene_desc[:250])}</i>")

    # Summary (truncated safely if needed)
    if summary:
        lines.append("")
        max_summary_len = 300
        truncated_summary = summary[:max_summary_len] + "..." if len(summary) > max_summary_len else summary
        lines.append(f"{get_msg(lang, 'label_summary')}\n{html.escape(truncated_summary)}")

    lines.append("")
    lines.append(get_msg(lang, "label_found_by"))

    full_text = "\n".join(lines)
    if len(full_text) > max_len:
        return full_text[:max_len - 10] + "..."
    return full_text
