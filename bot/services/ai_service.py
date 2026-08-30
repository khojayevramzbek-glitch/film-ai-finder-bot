import os
import glob
import json
import time
import uuid
import random
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

from bot.config import GEMINI_API_KEYS, GEMINI_MODEL, DOWNLOAD_DIR
from bot.services.key_manager import APIKeyPool

logger = logging.getLogger(__name__)

# Initialize Key Pool for Gemini
gemini_key_pool = APIKeyPool(keys=GEMINI_API_KEYS, service_name="Gemini AI", default_cooldown=60)

FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash"
]


def build_system_prompt(lang: str = "uz") -> str:
    """Builds prompt instructing Gemini in user's target language."""
    lang_rules = {
        "uz": "Javobdagi qisqacha mazmun (summary), sahna tavsifi (scene_description) va sabablarni O'ZBEK tilida (lotin) yozing.",
        "uz_kr": "Жавобдаги қисқача мазмун (summary), саҳна тавсифи (scene_description) ва сабабларни ЎЗБЕК тилида (кирилл алифбосида) ёзинг.",
        "ru": "Краткое описание сюжета (summary), описание сцены из видео (scene_description) и причину пишите на РУССКОМ языке.",
        "en": "Write the plot summary (summary), video scene description (scene_description), and confidence reason in ENGLISH."
    }
    target_rule = lang_rules.get(lang, lang_rules["uz"])

    return f"""
Siz kino, serial, multfilm, anime va premyeralarni aniqlovchi professional sun'iy intellekt ekspertisiz.

Sizga videodan olingan asosiy kadrlar (yoki bitta rasm/skrinshot yoki matnli syujet/sarlavha/kayfiyat) beriladi.
Vazifangiz: Berilgan ma'lumotdan foydalanib, bu qaysi kino, serial, multfilm, dorama yoki animatsiya ekanligini ANIQ aniqlash yoki tavsiya etish.

JUDA MUHIM QOIDALAR:
1. Agar bu kino/serial hali rasman chiqmagan bo'lsa (masalan yaqinda e'lon qilingan treyler, tizer yoki kelgusi premyera), "is_premiere": true deb belgilang va kutilayotgan premyera sanasini/yilini yozing.
2. Agar bu mavjud film yoki serial bo'lsa, asl nomini (original title), o'zbekcha va ruscha tarjimalarini bering.
3. Media turini aniq belgilang: "movie", "series", "cartoon", "anime", "trailer".
4. {target_rule}

Javobni FAQAT quyidagi toza JSON formatida qaytaring:
```json
{{
  "found": true,
  "title_original": "Original Title (e.g. Inception, Avatar, Spider-Man)",
  "title_uz": "O'zbekcha nomi",
  "title_ru": "Русское название",
  "media_type": "movie | series | cartoon | anime | trailer",
  "release_year": "2025",
  "is_premiere": false,
  "premiere_date": null,
  "confidence": "high",
  "characters_or_actors": ["Actor 1", "Character name"],
  "scene_description": "Videoda/suratda qaysi sahna tasvirlangani",
  "summary": "Filmning qisqacha mazmuni",
  "confidence_reason": "Nima belgilar orqali aniqlandi"
}}
```

Agar berilgan ma'lumotda hech qanday kino, serial, anime yoki multfilm topilmasa:
```json
{{
  "found": false,
  "reason": "Film yoki serial aniqlanmadi."
}}
```
"""


class AIService:
    """Service to interact with Gemini API with multi-key rotation and multi-modal search."""

    def __init__(self):
        self.pool = gemini_key_pool
        self.model_name = GEMINI_MODEL

    def _extract_keyframes(self, video_path: Path, num_frames: int = 5) -> List[Path]:
        """Extracts keyframes from video in milliseconds using FFmpeg."""
        if not FFMPEG_EXE or not os.path.exists(FFMPEG_EXE):
            return []

        frame_prefix = DOWNLOAD_DIR / f"frame_{uuid.uuid4().hex[:8]}"
        out_pattern = f"{frame_prefix}_%02d.jpg"

        try:
            cmd = [
                FFMPEG_EXE,
                "-i", str(video_path),
                "-vf", "fps=1/2,scale=640:-1",
                "-vframes", str(num_frames),
                "-q:v", "4",
                out_pattern,
                "-y"
            ]
            subprocess.run(cmd, capture_output=True, timeout=5)
            created_frames = sorted(Path(p) for p in glob.glob(f"{frame_prefix}_*.jpg"))
            return created_frames
        except Exception as e:
            logger.warning(f"[Frame Extraction Warning] Kadrlar ajratib olinmadi: {e}")
            return []

    def _execute_gemini_request(self, contents: List[Any], response_json: bool = True, temperature: float = 0.3) -> Optional[str]:
        """Executes request with auto-retry, custom temperature, and multi-key rotation."""
        if self.pool.is_empty():
            return None

        max_attempts = max(self.pool.total_count, 1)
        models_to_try = [m for m in FALLBACK_MODELS if m]

        for attempt in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break

            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)

                config_kwargs = {"temperature": temperature}
                if response_json:
                    config_kwargs["response_mime_type"] = "application/json"

                response = None
                for model_candidate in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_candidate,
                            contents=contents,
                            config=types.GenerateContentConfig(**config_kwargs)
                        )
                        self.model_name = model_candidate
                        break
                    except Exception as model_err:
                        err_text = str(model_err).lower()
                        if "404" in err_text or "not found" in err_text or "429" in err_text or "quota" in err_text:
                            continue
                        raise model_err

                if response and response.text:
                    self.pool.report_success(api_key)
                    return response.text

            except Exception as e:
                err_str = str(e)
                is_rate_limit = any(term in err_str.lower() for term in [
                    "429", "quota", "resourceexhausted", "rate limit", "exceeded"
                ])
                if is_rate_limit:
                    self.pool.report_rate_limit(api_key, cooldown_seconds=60)
                else:
                    self.pool.report_rate_limit(api_key, cooldown_seconds=20)
                continue

        return None

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Cleans and parses JSON output from Gemini."""
        if not text:
            return {"found": False, "reason": "Javob olinmadi."}
        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"[JSON Parse Error] Javobni JSON ga o'girib bo'lmadi: {e}\nMatn: {text}")
            return {"found": False, "reason": "AI javobini qayta ishlashda xatolik."}

    # 1. Video Analysis
    def _sync_analyze_video(self, video_path: Path, metadata_text: str = "", lang: str = "uz") -> Dict[str, Any]:
        frames = self._extract_keyframes(video_path, num_frames=5)
        contents = []

        from google.genai import types

        if frames:
            for frame_path in frames:
                with open(frame_path, "rb") as f:
                    contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

        system_prompt = build_system_prompt(lang=lang)
        prompt_content = f"{system_prompt}\n\nQo'shimcha metadata / Sarlavha: {metadata_text}"
        contents.append(prompt_content)

        resp_text = self._execute_gemini_request(contents, response_json=True, temperature=0.3)

        for f_path in frames:
            try:
                if f_path.exists():
                    f_path.unlink()
            except Exception:
                pass

        return self._parse_json_response(resp_text)

    async def analyze_video(self, video_path: Path, metadata_text: str = "", lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_analyze_video, video_path, metadata_text, lang)

    # 2. Image / Screenshot Analysis
    def _sync_analyze_image(self, image_path: Path, caption: str = "", lang: str = "uz") -> Dict[str, Any]:
        from google.genai import types
        contents = []
        with open(image_path, "rb") as f:
            contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

        system_prompt = build_system_prompt(lang=lang)
        prompt_content = f"{system_prompt}\n\nFoydalanuvchi yuborgan rasm/skrinshot. Qo'shimcha izoh: {caption}"
        contents.append(prompt_content)

        resp_text = self._execute_gemini_request(contents, response_json=True, temperature=0.3)
        return self._parse_json_response(resp_text)

    async def analyze_image(self, image_path: Path, caption: str = "", lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_analyze_image, image_path, caption, lang)

    # 3. Plot Description & Mood-Based Text Search
    def _sync_analyze_plot_text(self, text_input: str, lang: str = "uz") -> Dict[str, Any]:
        system_prompt = build_system_prompt(lang=lang)
        prompt_content = (
            f"{system_prompt}\n\n"
            f"Foydalanuvchi quyidagi matnni yozdi (bu unutilgan film syujeti, kino qahramonlari yoki ko'rishni xohlayotgan kayfiyati bo'lishi mumkin):\n"
            f"\"{text_input}\"\n\n"
            f"Ushbu tavsifga yoki kayfiyatga eng mukammal mos keluvchi haqiqiy film, serial, anime yoki multfilmni toping va ma'lumotlarini bering."
        )
        resp_text = self._execute_gemini_request([prompt_content], response_json=True, temperature=0.4)
        return self._parse_json_response(resp_text)

    async def analyze_plot_text(self, text_input: str, lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_analyze_plot_text, text_input, lang)

    # 4. Similar Movies Recommendations
    def _sync_get_similar_movies(self, title: str, lang: str = "uz") -> List[Dict[str, Any]]:
        lang_instruction = {
            "uz": "Tavsiflarni O'zbek tilida (lotin) yozing.",
            "uz_kr": "Тавсифларни Ўзбек тилида (кирилл) ёзинг.",
            "ru": "Описания пишите на русском языке.",
            "en": "Write descriptions in English."
        }.get(lang, "Tavsiflarni O'zbek tilida yozing.")

        prompt = f"""
Siz professional kino tavsiya etuvchi sun'iy intellektsiz.
Foydalanuvchiga "{title}" filmiga mavzusi, janri, atmosferasi va uslubi bo'yicha eng yaqin va eng zo'r 3 TA O'XSHASH FILMNI tavsiya qiling.

{lang_instruction}

Javobni FAQAT quyidagi JSON ro'yxati formatida qaytaring:
```json
[
  {{
    "title": "Movie Title",
    "year": "2023",
    "genres": "Janri",
    "reason": "Nima uchun ushbu filmga o'xshash va nima uchun ko'rish tavsiya etiladi"
  }}
]
```
"""
        resp_text = self._execute_gemini_request([prompt], response_json=True, temperature=0.5)
        try:
            cleaned = resp_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return data if isinstance(data, list) else []
        except Exception:
            return []

    async def get_similar_movies(self, title: str, lang: str = "uz") -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._sync_get_similar_movies, title, lang)

    # 5. /random AI Movie Curator (Genres, Moods, and Surprise Me!)
    def _sync_get_random_movie(self, genre_or_mood: str, exclude_title: str = "", lang: str = "uz") -> Dict[str, Any]:
        lang_instruction = {
            "uz": "Mazmun va tavsiyani O'zbek tilida (lotin) yozing.",
            "uz_kr": "Мазмун ва тавсияни Ўзбек тилида (кирилл) ёзинг.",
            "ru": "Сюжет и рекомендацию пишите на русском языке.",
            "en": "Write summary and recommendation in English."
        }.get(lang, "Mazmunni O'zbek tilida yozing.")

        random_seed = random.randint(1000, 99999)
        exclude_clause = ""
        if exclude_title:
            exclude_clause = f"JUDA MUHIM: Quyidagi filmlarni TAVSIYA QILMANG (foydalanuvchi buni ko'rgan): \"{exclude_title}\". Mutlaqo boshqa, yangi film tanlang!"

        is_surprise = "surprise" in genre_or_mood.lower() or "hayrat" in genre_or_mood.lower()

        if is_surprise:
            genres_pool = ["Aqlbovar qilmas Fantastika", "Kutilmagan burilishlarga boy Triller", "Chuqur Psixologik Drama", "Hayotbaxsh va Ilhomlantiruvchi Sarguzasht", "Kult klassika"]
            picked_style = random.choice(genres_pool)
            task_description = f"Butun dunyo kinematografiyasidagi eng sara, yuqori reytingli (IMDb 8+) va tomoshabinni lol qoldiradigan 1 TA AQLBOVAR QILMAS DURDONA FILMNI ({picked_style}) tanlang."
        else:
            task_description = f"\"{genre_or_mood}\" janri yoki kayfiyatiga mos, eng sara, qiziqarli va yuqori reytingli 1 TA FILMNI tanlang."

        prompt = f"""
Siz butun dunyo kinematografiyasini mukammal biluvchi Sun'iy Intellekt Kino Kuratorisiz.
Foydalanuvchi bugun kechqurun maroq bilan ko'rish uchun quyidagi so'rovni yubordi:
{task_description}

Tasodifiy seed: #{random_seed}
{exclude_clause}

{lang_instruction}

Javobni FAQAT quyidagi JSON formatida qaytaring:
```json
{{
  "title_original": "Movie Title",
  "title_local": "Mahalliy nomi",
  "release_year": "2022",
  "rating": "8.5",
  "genres": "{genre_or_mood if not is_surprise else 'Top Masterpiece'}",
  "actors": ["Actor 1", "Actor 2"],
  "summary": "Filmning qisqacha maftunkor syujeti",
  "why_watch": "Nima uchun aynan shu filmni ko'rish shart (taassurot va kayfiyat)"
}}
```
"""
        resp_text = self._execute_gemini_request([prompt], response_json=True, temperature=0.95)
        return self._parse_json_response(resp_text)

    async def get_random_movie(self, genre_or_mood: str, exclude_title: str = "", lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_get_random_movie, genre_or_mood, exclude_title, lang)


ai_service = AIService()
