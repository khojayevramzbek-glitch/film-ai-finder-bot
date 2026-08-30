import os
import glob
import json
import time
import uuid
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
    GEMINI_MODEL,
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-3-flash-preview",
    "gemini-2.5-pro",
    "gemini-pro-latest"
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

Sizga videodan olingan asosiy kadrlar (yoki video) va uning sarlavhasi/tavsifi beriladi.
Vazifangiz: Kadrlardagi qahramonlar, aktyorlar, yuzlar, kiyimlar, sahna detallari va kontekstdan foydalanib, bu qaysi kino, serial, multfilm, dorama yoki animatsiya ekanligini ANIQ aniqlash.

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
  "scene_description": "Videoda qaysi sahna sodir bo'layotgani haqida",
  "summary": "Filmning qisqacha mazmuni",
  "confidence_reason": "Nima belgilar orqali aniqlandi"
}}
```

Agar videoda hech qanday film, serial, anime yoki multfilm lavhasi bo'lmasa (oddiy vblog, shaxsiy video, oddiy mem):
```json
{{
  "found": false,
  "reason": "Videoda hech qanday film yoki serial lavhasi topilmadi."
}}
```
"""


class AIService:
    """Service to interact with Gemini API with instant frame extraction, multi-key rotation, and auto-failover."""

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
                "-vf", f"fps=1/2,scale=640:-1",
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

    def _sync_analyze_video(self, video_path: Path, metadata_text: str = "", lang: str = "uz") -> Dict[str, Any]:
        """
        Analyzes video in user's target language using keyframes for ultra-fast response.
        """
        if self.pool.is_empty():
            return {
                "found": False,
                "reason": "Gemini API kaliti sozlanmagan (.env fayliga GEMINI_API_KEYS kiriting)."
            }

        frames = self._extract_keyframes(video_path, num_frames=5)
        max_attempts = max(self.pool.total_count, 1)
        last_error = ""

        models_to_try = []
        for m in FALLBACK_MODELS:
            if m and m not in models_to_try:
                models_to_try.append(m)

        system_prompt = build_system_prompt(lang=lang)

        for attempt in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break

            masked_key = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "***"
            logger.info(f"[AI Service] Gemini so'rovi yuborilmoqda (Kalit: {masked_key}, Til: {lang}, Urinish: {attempt + 1}/{max_attempts})")

            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)

                contents = []
                uploaded_file = None

                if frames:
                    for frame_path in frames:
                        with open(frame_path, "rb") as f:
                            contents.append(types.Part.from_bytes(data=f.read(), mime_type="image/jpeg"))
                else:
                    uploaded_file = client.files.upload(file=str(video_path))
                    while uploaded_file.state == "PROCESSING":
                        time.sleep(2)
                        uploaded_file = client.files.get(name=uploaded_file.name)
                    contents.append(uploaded_file)

                prompt_content = f"{system_prompt}\n\nQo'shimcha metadata / Sarlavha: {metadata_text}"
                contents.append(prompt_content)

                response = None
                for model_candidate in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_candidate,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                temperature=0.2,
                                response_mime_type="application/json"
                            )
                        )
                        self.model_name = model_candidate
                        break
                    except Exception as model_err:
                        if "404" in str(model_err) or "not found" in str(model_err).lower():
                            logger.warning(f"Model {model_candidate} mavjud emas, keyingisiga o'tilmoqda...")
                            continue
                        raise model_err

                if uploaded_file:
                    try:
                        client.files.delete(name=uploaded_file.name)
                    except Exception:
                        pass

                for f_path in frames:
                    try:
                        if f_path.exists():
                            f_path.unlink()
                    except Exception:
                        pass

                if response and response.text:
                    self.pool.report_success(api_key)
                    return self._parse_json_response(response.text)

            except Exception as e:
                err_str = str(e)
                last_error = err_str
                is_rate_limit = any(term in err_str.lower() for term in [
                    "429", "quota", "resourceexhausted", "rate limit", "exceeded"
                ])

                if is_rate_limit:
                    logger.warning(f"⚠️ Limit xatosi: {err_str[:120]}... Keyingi kalitga o'tilmoqda!")
                    self.pool.report_rate_limit(api_key, cooldown_seconds=60)
                    continue
                else:
                    logger.error(f"[AI Service Error] Tahlilda xatolik: {e}")
                    self.pool.report_rate_limit(api_key, cooldown_seconds=30)
                    continue

        for f_path in frames:
            try:
                if f_path.exists():
                    f_path.unlink()
            except Exception:
                pass

        return {
            "found": False,
            "reason": f"Barcha API kalitlari bilan sinab ko'rildi, lekin tahlil qilib bo'lmadi ({last_error[:100]})."
        }

    @staticmethod
    def _parse_json_response(text: str) -> Dict[str, Any]:
        """Cleans and parses JSON output from Gemini."""
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
            return {
                "found": False,
                "reason": "AI javobini qayta ishlashda xatolik."
            }

    async def analyze_video(self, video_path: Path, metadata_text: str = "", lang: str = "uz") -> Dict[str, Any]:
        """Asynchronously analyze video with Gemini in user's target language."""
        return await asyncio.to_thread(self._sync_analyze_video, video_path, metadata_text, lang)


ai_service = AIService()
