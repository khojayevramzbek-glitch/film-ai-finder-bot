import aiohttp
import logging
from typing import Optional, Dict, Any, List
from bot.config import TMDB_API_KEYS
from bot.services.key_manager import APIKeyPool

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w780"

# Initialize Key Pool for TMDb
tmdb_key_pool = APIKeyPool(keys=TMDB_API_KEYS, service_name="TMDb", default_cooldown=60)


class TMDbService:
    """Service to fetch rich movie/TV metadata with multi-key rotation support."""

    def __init__(self):
        self.pool = tmdb_key_pool

    async def search_media(self, query: str, year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Searches for a movie or TV show with automatic key rotation and failover.
        """
        if self.pool.is_empty() or not query:
            return None

        query = query.strip()
        if not query:
            return None

        max_attempts = max(self.pool.total_count, 1)

        for attempt in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break

            try:
                async with aiohttp.ClientSession() as session:
                    # 1. Search Multi
                    search_url = f"{TMDB_BASE_URL}/search/multi"
                    params = {
                        "api_key": api_key,
                        "query": query,
                        "language": "ru-RU",
                        "include_adult": "false"
                    }
                    if year and year.isdigit():
                        params["year"] = year

                    async with session.get(search_url, params=params, timeout=10) as resp:
                        if resp.status == 429:
                            self.pool.report_rate_limit(api_key, cooldown_seconds=60)
                            continue
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                        results = data.get("results", [])

                    if not results:
                        # Fallback to English query
                        params["language"] = "en-US"
                        async with session.get(search_url, params=params, timeout=10) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                results = data.get("results", [])

                    if not results:
                        self.pool.report_success(api_key)
                        return None

                    # Pick the best match
                    media_item = None
                    for item in results:
                        if item.get("media_type") in ["movie", "tv"]:
                            media_item = item
                            break

                    if not media_item:
                        self.pool.report_success(api_key)
                        return None

                    media_id = media_item.get("id")
                    media_type = media_item.get("media_type")

                    # 2. Full details
                    detail_url = f"{TMDB_BASE_URL}/{media_type}/{media_id}"
                    detail_params = {
                        "api_key": api_key,
                        "language": "ru-RU",
                        "append_to_response": "videos,credits,external_ids"
                    }

                    async with session.get(detail_url, params=detail_params, timeout=10) as resp:
                        if resp.status == 429:
                            self.pool.report_rate_limit(api_key, cooldown_seconds=60)
                            continue
                        if resp.status != 200:
                            continue
                        detail = await resp.json()

                    self.pool.report_success(api_key)

                    # Extract fields
                    title = detail.get("title") or detail.get("name") or query
                    original_title = detail.get("original_title") or detail.get("original_name") or title
                    overview = detail.get("overview") or media_item.get("overview", "")
                    
                    release_date = detail.get("release_date") or detail.get("first_air_date") or ""
                    release_year = release_date.split("-")[0] if release_date else (year or "")
                    status = detail.get("status", "")
                    is_premiere = status in ["In Production", "Post Production", "Planned", "Upcoming"]

                    poster_path = detail.get("poster_path") or media_item.get("poster_path")
                    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None
                    backdrop_path = detail.get("backdrop_path")
                    backdrop_url = f"{TMDB_IMAGE_BASE}{backdrop_path}" if backdrop_path else None

                    vote_avg = detail.get("vote_average", 0)
                    rating = round(vote_avg, 1) if vote_avg > 0 else None

                    genres = [g.get("name") for g in detail.get("genres", []) if g.get("name")]

                    credits = detail.get("credits", {})
                    cast = [c.get("name") for c in credits.get("cast", [])[:5] if c.get("name")]

                    videos = detail.get("videos", {}).get("results", [])
                    trailer_url = None
                    for vid in videos:
                        if vid.get("site") == "YouTube" and vid.get("type") in ["Trailer", "Teaser"]:
                            trailer_url = f"https://www.youtube.com/watch?v={vid.get('key')}"
                            break

                    imdb_id = detail.get("external_ids", {}).get("imdb_id") or detail.get("imdb_id")

                    return {
                        "tmdb_id": media_id,
                        "imdb_id": imdb_id,
                        "title": title,
                        "original_title": original_title,
                        "title_ru": title,
                        "media_type": media_type,
                        "release_date": release_date,
                        "year": release_year,
                        "is_premiere": is_premiere,
                        "status": status,
                        "rating": rating,
                        "genres": genres,
                        "cast": cast,
                        "overview": overview,
                        "poster_url": poster_url,
                        "backdrop_url": backdrop_url,
                        "trailer_url": trailer_url,
                        "tmdb_url": f"https://www.themoviedb.org/{media_type}/{media_id}"
                    }

            except Exception as e:
                logger.error(f"[TMDb Error] Qidiruvda xatolik: {e}")
                self.pool.report_rate_limit(api_key, cooldown_seconds=30)
                continue

        return None


tmdb_service = TMDbService()
