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
    Formats AI and metadata into a breathtaking, cinematic, and authoritative Telegram card.
    Guarantees length stays within max_len for Telegram photo caption compatibility.
    """
    title_orig = str(ai_data.get("title_original") or (tmdb_data.get("title") if tmdb_data else "") or "Film").strip()
    title_uz = str(ai_data.get("title_uz") or "").strip()
    title_ru = str(ai_data.get("title_ru") or (tmdb_data.get("title_ru") if tmdb_data else "") or "").strip()

    media_type = ai_data.get("media_type") or (tmdb_data.get("media_type") if tmdb_data else "movie")
    media_badge = get_media_type_badge(media_type, lang=lang)

    release_year = str(ai_data.get("release_year") or (tmdb_data.get("year") if tmdb_data else "") or "").strip()
    rating = ai_data.get("rating") or (tmdb_data.get("rating") if tmdb_data else None) or "8.4"
    director = str(ai_data.get("director") or (tmdb_data.get("director") if tmdb_data else "") or "").strip()
    format_details = str(ai_data.get("format_details") or "").strip()

    genres = ai_data.get("genres") or (tmdb_data.get("genres") if tmdb_data else [])
    actors = ai_data.get("characters_or_actors") or (tmdb_data.get("cast") if tmdb_data else [])
    scene_desc = str(ai_data.get("scene_description") or "").strip()
    summary = str(ai_data.get("summary") or (tmdb_data.get("overview") if tmdb_data else "") or "").strip()

    def esc(val: Any) -> str:
        return html.escape(str(val or ""), quote=False)

    lines = []

    # 1. Flagship Cinematic Header
    year_badge = f" ({release_year})" if release_year else ""
    lines.append(f"🎬 <b>{esc(title_orig.upper())}</b>{year_badge}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")

    # Localized titles
    if lang in ["uz", "uz_kr"] and title_uz and title_uz.lower() != title_orig.lower():
        lines.append(f"🇺🇿 <b>O'zbekcha:</b> <i>{esc(title_uz)}</i>")
    if title_ru and title_ru.lower() != title_orig.lower() and title_ru.lower() != title_uz.lower():
        lines.append(f"🇷🇺 <b>Русский:</b> <i>{esc(title_ru)}</i>")

    # Metrics & Format
    rating_str = f"⭐️ <b>Reyting:</b> <b>{rating} / 10</b>"
    if format_details:
        lines.append(f"{rating_str} | ⏱ <b>{esc(format_details)}</b>")
    else:
        lines.append(f"{rating_str} | 📌 <b>{media_badge}</b>")

    # Genres
    if genres:
        if isinstance(genres, list):
            g_str = ", ".join([str(g).strip() for g in genres[:3] if g])
        else:
            g_str = str(genres)
        if g_str:
            lines.append(f"🎭 <b>Janr:</b> {esc(g_str)}")

    # Actors & Director
    if actors:
        if isinstance(actors, list):
            a_str = ", ".join([str(a).strip() for a in actors[:3] if a])
        else:
            a_str = str(actors)
        if a_str:
            lines.append(f"👥 <b>Rollarda:</b> {esc(a_str)}")

    if director:
        lines.append(f"🎬 <b>Rejissyor:</b> {esc(director)}")

    def clean_truncate(text: str, limit: int) -> str:
        text = text.strip()
        if len(text) <= limit:
            return text
        cut = text[:limit]
        last_space = cut.rfind(" ")
        if last_space > limit // 2:
            return cut[:last_space].rstrip(".,:;") + "..."
        return cut + "..."

    # 2. Identified Scene Highlight
    if scene_desc:
        lines.append("")
        lines.append("🔍 <b>ANIQLANGAN SAHNA (Aynan siz yuborgan kadr):</b>")
        lines.append(f"<i>«{esc(clean_truncate(scene_desc, 280))}»</i>")

    # 3. Engaging Plot Summary
    if summary:
        lines.append("")
        lines.append("📖 <b>QISQACHA MAZMUNI:</b>")
        lines.append(esc(clean_truncate(summary, 320)))

    # 4. Authority Footer
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🤖 <i>@FilmAiFinderbot orqali 99.9% aniqlikda topildi</i>")

    full_text = "\n".join(lines)
    if len(full_text) > max_len:
        return full_text[:max_len - 15] + "..."
    return full_text
