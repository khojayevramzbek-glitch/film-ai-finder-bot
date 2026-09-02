import aiohttp
import logging
from typing import Optional, Dict, Any, List
from bot.config import TMDB_API_KEYS
from bot.services.key_manager import APIKeyPool

logger = logging.getLogger(__name__)

# Initialize Key Pool for TMDb
tmdb_key_pool = APIKeyPool(keys=TMDB_API_KEYS, service_name="TMDb", default_cooldown=60)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


class TMDbService:
    """Service to interact with TMDb API with multi-key rotation."""

    def __init__(self):
        self.pool = tmdb_key_pool

    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Makes an HTTP GET request using an active TMDb API key from the pool."""
        if self.pool.is_empty():
            return None

        max_attempts = max(self.pool.total_count, 1)

        for attempt in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break

            req_params = dict(params)
            req_params["api_key"] = api_key

            try:
                async with aiohttp.ClientSession() as session:
                    url = f"{TMDB_BASE_URL}{endpoint}"
                    async with session.get(url, params=req_params, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                        if resp.status == 200:
                            self.pool.report_success(api_key)
                            return await resp.json()
                        elif resp.status in (429, 401, 403):
                            self.pool.report_rate_limit(api_key, cooldown_seconds=60)
                            continue
                        else:
                            return None
            except Exception as e:
                logger.warning(f"[TMDb Request Warning] {e}")
                self.pool.report_rate_limit(api_key, cooldown_seconds=15)
                continue

        return None

    @staticmethod
    async def fetch_fallback_poster(title: str) -> Optional[str]:
        """Fetches HD movie poster from iTunes or Wikipedia without requiring any API keys."""
        import urllib.parse
        headers = {"User-Agent": "FilmFinderBot/3.5 (admin@filmfinder.uz)"}

        # 1. Try iTunes Movie / TV
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(title)}&limit=1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if data.get("resultCount", 0) > 0:
                            artwork = data["results"][0].get("artworkUrl100", "")
                            if artwork:
                                return artwork.replace("100x100bb", "600x600bb")
        except Exception:
            pass

        # 2. Try Wikipedia
        try:
            clean_title = title.replace(" ", "_")
            wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_title)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(wiki_url, headers=headers, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        img = data.get("originalimage", {}).get("source") or data.get("thumbnail", {}).get("source")
                        if img:
                            return img
        except Exception:
            pass

        return None

    async def search_media(self, title: str, year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Searches TMDb for a movie or TV show, with multi-engine fallback for posters."""
        if not title:
            return None

        import urllib.parse
        params = {"query": title, "include_adult": "false"}
        if year and year.isdigit():
            params["year"] = year

        data = await self._make_request("/search/multi", params)
        if not data or not data.get("results"):
            if "year" in params:
                del params["year"]
                data = await self._make_request("/search/multi", params)

        if data and data.get("results"):
            for item in data["results"]:
                media_type = item.get("media_type")
                if media_type in ("movie", "tv"):
                    details = await self._extract_details(item, media_type)
                    if not details.get("poster_url"):
                        details["poster_url"] = await self.fetch_fallback_poster(title)
                    return details

        # Universal Fallback (when TMDb has no key or finds nothing)
        fallback_poster = await self.fetch_fallback_poster(title)
        return {
            "id": None,
            "title": title,
            "original_title": title,
            "media_type": "movie",
            "year": year or "",
            "poster_url": fallback_poster,
            "rating": None,
            "overview": "",
            "trailer_url": f"https://www.youtube.com/results?search_query={urllib.parse.quote(title)}+official+trailer",
            "imdb_id": None,
            "genres": [],
            "cast": []
        }

    async def _extract_details(self, item: Dict[str, Any], media_type: str) -> Dict[str, Any]:
        """Extracts and enriches media details including trailer and genres."""
        item_id = item.get("id")
        title = item.get("title") or item.get("name") or "Noma'lum"
        original_title = item.get("original_title") or item.get("original_name") or title
        release_date = item.get("release_date") or item.get("first_air_date") or ""
        year = release_date[:4] if release_date else ""

        poster_path = item.get("poster_path")
        poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

        vote_average = item.get("vote_average", 0.0)
        overview = item.get("overview", "")

        trailer_url = None
        imdb_id = None
        runtime = None

        if item_id:
            details_endpoint = f"/{media_type}/{item_id}"
            details_data = await self._make_request(details_endpoint, {"append_to_response": "videos,external_ids"})
            if details_data:
                runtime = details_data.get("runtime") or (details_data.get("episode_run_time", [None])[0] if details_data.get("episode_run_time") else None)
                external_ids = details_data.get("external_ids", {})
                imdb_id = external_ids.get("imdb_id")

                videos = details_data.get("videos", {}).get("results", [])
                for v in videos:
                    if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
                        trailer_url = f"https://www.youtube.com/watch?v={v.get('key')}"
                        if v.get("type") == "Trailer":
                            break

        tmdb_url = f"https://www.themoviedb.org/{media_type}/{item_id}" if item_id else None

        return {
            "id": item_id,
            "title": title,
            "original_title": original_title,
            "media_type": media_type,
            "year": year,
            "poster_url": poster_url,
            "rating": round(float(vote_average), 1) if vote_average else None,
            "overview": overview,
            "trailer_url": trailer_url,
            "imdb_id": imdb_id,
            "runtime": runtime,
            "tmdb_url": tmdb_url
        }

    async def search_person(self, name: str) -> Optional[Dict[str, Any]]:
        """Searches TMDb for an actor or director to fetch profile image."""
        if not name:
            return None

        data = await self._make_request("/search/person", {"query": name, "include_adult": "false"})
        if not data or not data.get("results"):
            return None

        person = data["results"][0]
        profile_path = person.get("profile_path")
        profile_url = f"{TMDB_IMAGE_BASE}{profile_path}" if profile_path else None

        return {
            "id": person.get("id"),
            "name": person.get("name"),
            "known_for_department": person.get("known_for_department"),
            "profile_url": profile_url,
            "popularity": person.get("popularity")
        }


tmdb_service = TMDbService()
