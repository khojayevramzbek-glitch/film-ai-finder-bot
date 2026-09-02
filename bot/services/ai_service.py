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
from bot.services.groq_service import groq_service

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
    """Builds prompt instructing Gemini in user's target language with strict Vision-First rules."""
    lang_rules = {
        "uz": "Javobdagi qisqacha mazmun (summary), sahna tavsifi (scene_description) va sabablarni O'ZBEK tilida (lotin) yozing.",
        "uz_kr": "Жавобдаги қисқача мазмун (summary), саҳна тавсифи (scene_description) ва сабабларни ЎЗБЕК тилида (кирилл алифбосида) ёзинг.",
        "ru": "Краткое описание сюжета (summary), описание сцены из видео (scene_description) и причину пишите на РУССКОМ языке.",
        "en": "Write the plot summary (summary), video scene description (scene_description), and confidence reason in ENGLISH."
    }
    target_rule = lang_rules.get(lang, lang_rules["uz"])

    return f"""
Siz kino, serial, multfilm, anime va premyeralarni aniqlovchi professional sun'iy intellekt ekspertisiz.

Sizga videodan olingan kadrlar (yoki rasm/skrinshot yoki matn) beriladi.
Vazifangiz: Berilgan kadrlardan foydalanib, bu qaysi haqiqiy kino, serial, multfilm yoki jangari film ekanligini ANIQ aniqlash.

O'TA MUHIM QOIDALAR:
1. ⚠️ DIQQAT: Instagram Reels, TikTok va YouTube Shorts mualliflari ko'pincha videoga mutlaqo aloqasi bo'lmagan soxta xeshteglar (masalan: #anime, #onepiece, #fyp, trend musiqalar nomini) yozib qo'yishadi.
2. 👁 FAQAT VIZUAL KADRLARGA ISHONING! Agar kadrlarda haqiqiy aktyorlar jangi (masalan: ringdagi jang, Yuri Boyka / Undisputed, Marvel, Jon Uik yoki Gollivud filmlari) ko'rinib tursa, muallif tagiga har qancha anime yoki boshqa so'z yozgan bo'lsa ham, MATNGA ALDANMANG! Kadrdagi haqiqiy film/aktyorni aniqlang!
3. Agar bu kino/serial hali chiqmagan bo'lsa, "is_premiere": true deb belgilang.
4. Haqiqiy filmning asl nomini (title_original) bering.
5. Media turini to'g'ri belgilang: "movie", "series", "cartoon", "anime", "trailer".
6. {target_rule}

Javobni FAQAT quyidagi toza JSON formatida qaytaring:
```json
{{
  "found": true,
  "title_original": "Original Title (e.g. Undisputed II: Last Man Standing, Inception, Avatar)",
  "title_uz": "O'zbekcha nomi (masalan: Bo'yko: Yengilmas)",
  "title_ru": "Русское название (masalan: Неоспоримый)",
  "media_type": "movie | series | cartoon | anime | trailer",
  "release_year": "2006",
  "is_premiere": false,
  "premiere_date": null,
  "confidence": "high",
  "characters_or_actors": ["Scott Adkins", "Yuri Boyka"],
  "scene_description": "Videoda/suratda qaysi jang yoki sahna aks etgani",
  "summary": "Filmning qisqacha mazmuni",
  "confidence_reason": "Kadrdagi aktyor (Scott Adkins) va qamoqxona ringidagi jang orqali aniqlandi"
}}
```

Agar berilgan ma'lumotda hech qanday kino topilmasa:
```json
{{
  "found": false,
  "reason": "Film yoki serial aniqlanmadi."
}}
```
"""


class AIService:
    """Service to interact with Gemini & Groq APIs with multi-key rotation and multi-modal search."""

    def __init__(self):
        self.pool = gemini_key_pool
        self.model_name = GEMINI_MODEL

    def _extract_keyframes(self, video_path: Path, num_frames: int = 6) -> List[Path]:
        """Extracts keyframes from video in milliseconds using FFmpeg."""
        if not FFMPEG_EXE or not os.path.exists(FFMPEG_EXE):
            return []

        frame_prefix = DOWNLOAD_DIR / f"frame_{uuid.uuid4().hex[:8]}"
        out_pattern = f"{frame_prefix}_%02d.jpg"

        try:
            cmd = [
                FFMPEG_EXE,
                "-i", str(video_path),
                "-vf", "fps=1,scale=720:-1",
                "-vframes", str(num_frames),
                "-q:v", "3",
                out_pattern,
                "-y"
            ]
            subprocess.run(cmd, capture_output=True, timeout=6)
            created_frames = sorted(Path(p) for p in glob.glob(f"{frame_prefix}_*.jpg"))
            return created_frames
        except Exception as e:
            logger.warning(f"[Frame Extraction Warning] Kadrlar ajratib olinmadi: {e}")
            return []

    def _execute_gemini_request(self, contents: List[Any], response_json: bool = True, temperature: float = 0.2) -> Optional[str]:
        """Executes request with auto-retry, custom temperature, and multi-key rotation."""
        if self.pool.is_empty():
            return None

        from bot.services.db import get_admin_setting

        # Dynamic AI model & temperature from Admin settings
        active_model = get_admin_setting("active_ai_model", self.model_name)
        try:
            dynamic_temp = float(get_admin_setting("ai_temperature", str(temperature)))
        except Exception:
            dynamic_temp = temperature

        max_attempts = max(self.pool.total_count, 1)
        models_to_try = [active_model] + [m for m in FALLBACK_MODELS if m and m != active_model]

        for attempt in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break

            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)

                config_kwargs = {"temperature": dynamic_temp}
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
        frames = self._extract_keyframes(video_path, num_frames=6)
        contents = []

        from google.genai import types
        from bot.services.downloader import DownloaderService
        from bot.services.groq_service import groq_service

        if frames:
            for frame_path in frames:
                with open(frame_path, "rb") as f:
                    contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))

        # Audio dialogue extraction (Whisper Turbo)
        audio_path = DownloaderService.extract_audio_snippet(video_path, max_duration_sec=30)
        dialogue_text = ""
        if audio_path:
            try:
                dialogue_text = groq_service._sync_transcribe_audio(audio_path)
            except Exception as e:
                logger.warning(f"[Audio Dialogue Error] {e}")
            finally:
                if audio_path.exists():
                    try:
                        audio_path.unlink()
                    except Exception:
                        pass

        system_prompt = build_system_prompt(lang=lang)
        prompt_content = f"{system_prompt}\n\n[ESLATMA: Asosiy e'tiborni videodagi kadrlar va aktyorlarga qarating!]"
        if dialogue_text:
            prompt_content += f"\n\n[VIDEODAGI NUTQ / DIALOGLAR (Transkripsiya)]: \"{dialogue_text}\""

        contents.append(prompt_content)

        resp_text = self._execute_gemini_request(contents, response_json=True, temperature=0.2)

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
        prompt_content = f"{system_prompt}\n\n[Foydalanuvchi yuborgan rasm. Faqat vizual kadrga qarab kinoni aniqlang!]"
        contents.append(prompt_content)

        resp_text = self._execute_gemini_request(contents, response_json=True, temperature=0.2)
        return self._parse_json_response(resp_text)

    async def analyze_image(self, image_path: Path, caption: str = "", lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_analyze_image, image_path, caption, lang)

    # 3. Plot Description & Mood-Based Text Search
    def _sync_analyze_plot_text(self, text_input: str, lang: str = "uz") -> Dict[str, Any]:
        system_prompt = build_system_prompt(lang=lang)
        prompt_content = (
            f"{system_prompt}\n\n"
            f"Foydalanuvchi quyidagi matnni yozdi:\n"
            f"\"{text_input}\"\n\n"
            f"Ushbu tavsifga eng mukammal mos keluvchi haqiqiy film yoki serialni toping."
        )
        resp_text = self._execute_gemini_request([prompt_content], response_json=True, temperature=0.3)
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

    # 5. Dual-Engine /random Movie Curator
    async def get_random_movie(self, genre_or_mood: str, exclude_title: str = "", lang: str = "uz") -> Dict[str, Any]:
        try:
            groq_res = await groq_service.get_random_movie(genre_or_mood, exclude_title, lang)
            if groq_res and groq_res.get("title_original"):
                return groq_res
        except Exception as e:
            logger.warning(f"[Groq Fallback Warning] {e}")

        return await asyncio.to_thread(self._sync_get_random_movie_gemini, genre_or_mood, exclude_title, lang)

    def _sync_get_random_movie_gemini(self, genre_or_mood: str, exclude_title: str = "", lang: str = "uz") -> Dict[str, Any]:
        lang_instruction = {
            "uz": "Mazmun va tavsiyani O'zbek tilida (lotin) yozing.",
            "uz_kr": "Мазмун ва тавсияни Ўзбек тилида (кирилл) ёзинг.",
            "ru": "Сюжет и рекомендацию пишите на русском языке.",
            "en": "Write summary and recommendation in English."
        }.get(lang, "Mazmunni O'zbek tilida yozing.")

        random_seed = random.randint(1000, 99999)
        exclude_clause = f"JUDA MUHIM: \"{exclude_title}\" filmini TAVSIYA QILMANG!" if exclude_title else ""
        prompt = f"""
Siz Sun'iy Intellekt Kino Kuratorisiz.
"{genre_or_mood}" bo'yicha eng zo'r 1 TA FILMNI tanlang. Seed: #{random_seed}. {exclude_clause}
{lang_instruction}

Javobni FAQAT JSON formatida qaytaring:
{{
  "title_original": "Movie Title",
  "title_local": "Mahalliy nomi",
  "release_year": "2022",
  "rating": "8.5",
  "genres": "{genre_or_mood}",
  "actors": ["Actor 1", "Actor 2"],
  "summary": "Filmning qisqacha maftunkor syujeti",
  "why_watch": "Nima uchun aynan shu filmni ko'rish shart"
}}
"""
        resp_text = self._execute_gemini_request([prompt], response_json=True, temperature=0.95)
        return self._parse_json_response(resp_text)

    # 6. Dual-Engine Interactive Movie Quiz
    async def generate_quiz(self, lang: str = "uz") -> Dict[str, Any]:
        try:
            groq_quiz = await groq_service.generate_quiz(lang)
            if groq_quiz and "question" in groq_quiz and "options" in groq_quiz:
                return groq_quiz
        except Exception as e:
            logger.warning(f"[Groq Quiz Fallback Warning] {e}")

        return await asyncio.to_thread(self._sync_generate_quiz_gemini, lang)

    def _sync_generate_quiz_gemini(self, lang: str = "uz") -> Dict[str, Any]:
        lang_instruction = {
            "uz": "Savol, variantlar va tushuntirishni O'ZBEK tilida (lotin) yozing.",
            "uz_kr": "Савол, вариантлар ва тушунтиришни ЎЗБЕК тилида (кирилл) ёзинг.",
            "ru": "Вопрос, варианты и объяснение пишите на РУССКОМ языке.",
            "en": "Write the question, options, and explanation in ENGLISH."
        }.get(lang, "Savolni O'zbek tilida yozing.")

        random_seed = random.randint(1000, 99999)
        prompt = f"""
Siz kino viktorina bo'yicha ekspert Sun'iy Intellektsiz.
Qiziqarli 1 TA KINO TEST SAVOLINI tuzing. Seed: #{random_seed}.
{lang_instruction}

Javobni FAQAT JSON formatida qaytaring:
{{
  "question": "Savol matni",
  "options": ["A javob", "B javob", "C javob", "D javob"],
  "correct_index": 0,
  "explanation": "Nima uchun ushbu javob to'g'riligi va qiziqarli fakt"
}}
"""
        resp_text = self._execute_gemini_request([prompt], response_json=True, temperature=0.9)
        return self._parse_json_response(resp_text)


ai_service = AIService()
