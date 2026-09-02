from __future__ import annotations
import json
import random
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from bot.config import GROQ_API_KEYS
from bot.services.key_manager import APIKeyPool
from bot.services.characters import get_character_info

logger = logging.getLogger(__name__)

# Initialize Groq Key Pool with 10 keys
groq_key_pool = APIKeyPool(keys=GROQ_API_KEYS, service_name="Groq AI (GPT-OSS / Qwen)", default_cooldown=30)

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "qwen/qwen3.8-27b"
]


class GroqService:
    """Ultra-fast Groq LPU inference engine for AI Movie Curator, Quizzes, Actor Explorer, and Character Roleplay."""

    def __init__(self):
        self.pool = groq_key_pool

    def _execute_groq(self, prompt: str, json_mode: bool = True, temperature: float = 0.8) -> Optional[str]:
        """Executes prompt via Groq API with multi-key rotation and multi-model fallback."""
        if self.pool.is_empty():
            return None

        max_attempts = max(self.pool.total_count, 1)

        for attempt in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break

            try:
                from groq import Groq
                client = Groq(api_key=api_key)

                for model in GROQ_MODELS:
                    try:
                        kwargs = {
                            "model": model,
                            "messages": [
                                {"role": "system", "content": "You are a professional cinema AI curator, movie trivia expert, and filmography biographer. Always return responses in valid clean JSON format only."},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": temperature,
                        }
                        if json_mode:
                            kwargs["response_format"] = {"type": "json_object"}

                        completion = client.chat.completions.create(**kwargs)
                        if completion.choices and completion.choices[0].message.content:
                            self.pool.report_success(api_key)
                            return completion.choices[0].message.content
                    except Exception as model_err:
                        err_str = str(model_err).lower()
                        if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                            self.pool.report_rate_limit(api_key, cooldown_seconds=30)
                            break
                        elif "404" in err_str or "model" in err_str:
                            continue
                        else:
                            raise model_err

            except Exception as e:
                logger.warning(f"[Groq Warning] Kalit {api_key[:8]}... xato berdi: {e}")
                self.pool.report_rate_limit(api_key, cooldown_seconds=20)
                continue

        return None

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parses and sanitizes JSON string."""
        if not text:
            return {}
        try:
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as e:
            logger.error(f"[Groq JSON Parse Error] {e}\nRaw: {text}")
            return {}

    # 1. Ultra-Fast /random Movie Curator
    def _sync_get_random_movie(self, genre_or_mood: str, exclude_title: str = "", lang: str = "uz") -> Dict[str, Any]:
        lang_instruction = {
            "uz": "Mazmun (summary) va tavsiyani (why_watch) O'zbek tilida (lotin) yozing.",
            "uz_kr": "Мазмун (summary) ва тавсияни (why_watch) Ўзбек тилида (кирилл) ёзинг.",
            "ru": "Сюжет (summary) и рекомендацию (why_watch) пишите на РУССКОМ языке.",
            "en": "Write summary and recommendation in ENGLISH."
        }.get(lang, "Mazmunni O'zbek tilida yozing.")

        random_seed = random.randint(1000, 99999)
        exclude_clause = ""
        if exclude_title:
            exclude_clause = f"JUDA MUHIM: Quyidagi filmlarni TAVSIYA QILMANG (foydalanuvchi buni ko'rgan): \"{exclude_title}\". Mutlaqo boshqa yangi film tanlang!"

        is_surprise = "surprise" in genre_or_mood.lower() or "hayrat" in genre_or_mood.lower()

        if is_surprise:
            styles = ["Aqlbovar qilmas Fantastika", "Kutilmagan burilishlarga boy Triller", "Chuqur Psixologik Drama", "Ilhomlantiruvchi Sarguzasht", "Kult klassika"]
            task_description = f"Butun dunyo kinematografiyasidagi eng sara, yuqori reytingli (IMDb 8+) va tomoshabinni hayratda qoldiradigan 1 TA AQLBOVAR QILMAS DURDONA FILMNI ({random.choice(styles)}) tanlang."
        else:
            task_description = f"\"{genre_or_mood}\" janri yoki kayfiyatiga mos eng sara, qiziqarli va yuqori reytingli 1 TA FILMNI tanlang."

        prompt = f"""
Siz jahon kinematografiyasini mukammal biluvchi Sun'iy Intellekt Kino Kuratorisiz.
Vazifa: {task_description}

Tasodifiylik kaliti: #{random_seed}
{exclude_clause}

{lang_instruction}

Javobni FAQAT quyidagi toza JSON formatida qaytaring:
{{
  "title_original": "Movie Title",
  "title_local": "Mahalliy nomi",
  "release_year": "2022",
  "rating": "8.6",
  "genres": "{genre_or_mood if not is_surprise else 'Top Masterpiece'}",
  "actors": ["Actor 1", "Actor 2"],
  "summary": "Filmning qisqacha maftunkor syujeti",
  "why_watch": "Nima uchun aynan shu filmni ko'rish shart"
}}
"""
        resp_text = self._execute_groq(prompt, json_mode=True, temperature=0.95)
        return self._parse_json(resp_text)

    async def get_random_movie(self, genre_or_mood: str, exclude_title: str = "", lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_get_random_movie, genre_or_mood, exclude_title, lang)

    # 2. Ultra-Fast AI Movie Quiz
    def _sync_generate_quiz(self, lang: str = "uz") -> Dict[str, Any]:
        lang_instruction = {
            "uz": "Savol (question), variantlar (options) va tushuntirishni (explanation) O'ZBEK tilida (lotin) yozing.",
            "uz_kr": "Савол, вариантлар ва тушунтиришни ЎЗБЕК тилида (кирилл) ёзинг.",
            "ru": "Вопрос, варианты и объяснение пишите на РУССКОМ языке.",
            "en": "Write question, options, and explanation in ENGLISH."
        }.get(lang, "Savolni O'zbek tilida yozing.")

        topics = [
            "mashhur kult filmning kutilmagan syujeti (plot twist)",
            "afsonaviy qahramonning mashhur iqtibosi (quote)",
            "mashhur Gollivud aktyorining o'ynagan roli",
            "Oskar olgan eng buyuk durdona film siri",
            "Garri Potter, Marvel, Avatar, Titanik yoki Qashqirlar Makoni filmlari"
        ]
        random_seed = random.randint(1000, 99999)

        prompt = f"""
Siz kino viktorina bo'yicha ekspert Sun'iy Intellektsiz.
Foydalanuvchilar uchun "{random.choice(topics)}" mavzusida juda qiziqarli 1 TA KINO TEST SAVOLINI tuzing.

Tasodifiy seed: #{random_seed}
{lang_instruction}

Javobni FAQAT quyidagi toza JSON formatida qaytaring:
{{
  "question": "Savol matni",
  "options": ["A javob", "B javob", "C javob", "D javob"],
  "correct_index": 0,
  "explanation": "Nima uchun ushbu javob to'g'riligi va film haqida qiziqarli fakt"
}}
"""
        resp_text = self._execute_groq(prompt, json_mode=True, temperature=0.9)
        return self._parse_json(resp_text)

    async def generate_quiz(self, lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_generate_quiz, lang)

    # 3. Actor & Director Filmography Explorer
    def _sync_get_actor_filmography(self, actor_name: str, lang: str = "uz") -> Dict[str, Any]:
        lang_instruction = {
            "uz": "Biografiya va tavsiflarni O'zbek tilida (lotin) yozing.",
            "uz_kr": "Биография ва тавсифларни Ўзбек тилида (кирилл) ёзинг.",
            "ru": "Биографию и описания пишите на РУССКОМ языке.",
            "en": "Write biography and descriptions in ENGLISH."
        }.get(lang, "Tavsiflarni O'zbek tilida yozing.")

        prompt = f"""
Siz jahon kinematografiyasi va aktyorlar/rejissyorlar bo'yicha eng nufuzli ekspert Sun'iy Intellektsiz.
Foydalanuvchi quyidagi shaxs haqida so'radi: "{actor_name}"

Vazifa:
1. Ushbu shaxsning to'liq ismi (person_name), kasbi (role) va 2 ta gapdan iborat qiziqarli ma'lumot/biografiyasi (bio).
2. Ushbu aktyor yoki rejissyorning butun faoliyatidagi ENG ENG SARA TOP-5 TA DURDONA FILMI (top_movies ro'yxati).
3. Har bir film uchun: nomi (title), yili (year), IMDb reytingi (rating), roli (role_name) va qisqacha tavsifi (description).

{lang_instruction}

Javobni FAQAT quyidagi toza JSON formatida qaytaring:
{{
  "found": true,
  "person_name": "Leonardo DiCaprio",
  "role": "Aktyor / Produser",
  "bio": "Gollivudning eng iste'dodli va nufuzli Oskar sohibi bo'lgan daho aktyorlaridan biri.",
  "top_movies": [
    {{
      "title": "Inception",
      "year": "2010",
      "rating": "8.8",
      "role_name": "Dom Cobb",
      "description": "Tushlar ichidagi operatsiyalar haqidagi aqlbovar qilmas shoh asar."
    }},
    {{
      "title": "The Wolf of Wall Street",
      "year": "2013",
      "rating": "8.2",
      "role_name": "Jordan Belfort",
      "description": "Uoll-Strit birjasidagi shov-shuvli hayot haqidagi kult film."
    }},
    {{
      "title": "Titanic",
      "year": "1997",
      "rating": "7.9",
      "role_name": "Jack Dawson",
      "description": "Dunyodagi eng mashhur fojiaviy muhabbat qissasi."
    }},
    {{
      "title": "The Revenant",
      "year": "2015",
      "rating": "8.0",
      "role_name": "Hugh Glass",
      "description": "Aktyorga orziqib kutilgan Oskarni keltirgan omon qolish dramasi."
    }},
    {{
      "title": "Shutter Island",
      "year": "2010",
      "rating": "8.2",
      "role_name": "Teddy Daniels",
      "description": "Ruhiy shifoxonadagi jumboqlarga to'la psixologik durdona."
    }}
  ]
}}
"""
        resp_text = self._execute_groq(prompt, json_mode=True, temperature=0.7)
        return self._parse_json(resp_text)

    async def get_actor_filmography(self, actor_name: str, lang: str = "uz") -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync_get_actor_filmography, actor_name, lang)

    # 4. Movie Character Live Roleplay Chat
    def _sync_chat_with_character(self, character_id: str, user_message: str, chat_history: List[Dict[str, str]] = None, lang: str = "uz") -> str:
        char_info = get_character_info(character_id)
        system_prompt = char_info["system_prompt"]

        lang_rule = {
            "uz": "Javobni O'zbek tilida (lotin yozuvida), o'z xarakteringizga xos bo'yoqdor va hissiyotli qilib bering.",
            "uz_kr": "Жавобни Ўзбек тилида (кирилл алифбосида) беринг.",
            "ru": "Отвечайте на РУССКОМ языке, строго сохраняя образ и манеру речи персонажа.",
            "en": "Respond in ENGLISH, strictly staying in character with full emotional depth."
        }.get(lang, "Javobni O'zbek tilida bering.")

        messages = [
            {"role": "system", "content": f"{system_prompt}\n\nLanguage Instruction: {lang_rule}"}
        ]

        if chat_history:
            for item in chat_history[-6:]:
                messages.append({"role": item.get("role", "user"), "content": item.get("content", "")})

        messages.append({"role": "user", "content": user_message})

        if self.pool.is_empty():
            return "..."

        max_attempts = max(self.pool.total_count, 1)

        for attempt in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break

            try:
                from groq import Groq
                client = Groq(api_key=api_key)

                for model in GROQ_MODELS:
                    try:
                        completion = client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=0.9,
                            max_tokens=500
                        )
                        if completion.choices and completion.choices[0].message.content:
                            self.pool.report_success(api_key)
                            return completion.choices[0].message.content.strip()
                    except Exception as model_err:
                        err_str = str(model_err).lower()
                        if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                            self.pool.report_rate_limit(api_key, cooldown_seconds=30)
                            break
                        elif "404" in err_str or "model" in err_str:
                            continue
                        else:
                            raise model_err

            except Exception as e:
                logger.warning(f"[Groq Roleplay Warning] {e}")
                self.pool.report_rate_limit(api_key, cooldown_seconds=20)
                continue

        return "..."

    async def chat_with_character(self, character_id: str, user_message: str, chat_history: List[Dict[str, str]] = None, lang: str = "uz") -> str:
        return await asyncio.to_thread(self._sync_chat_with_character, character_id, user_message, chat_history, lang)

    # 5. Ultra-Fast Groq Whisper Turbo Speech Recognition (~0.2s)
    def _sync_transcribe_audio(self, audio_path: Path) -> str:
        """Transcribes speech/audio in milliseconds using Groq Whisper Turbo."""
        if not audio_path.exists() or self.pool.is_empty():
            return ""

        max_attempts = max(self.pool.total_count, 1)
        for _ in range(max_attempts):
            api_key = self.pool.get_key()
            if not api_key:
                break
            try:
                from groq import Groq
                client = Groq(api_key=api_key)
                with open(audio_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(audio_path.name, file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                        temperature=0.0
                    )
                if transcription:
                    self.pool.report_success(api_key)
                    return str(transcription).strip()
            except Exception as e:
                logger.warning(f"[Groq Whisper Warning] {e}")
                self.pool.report_rate_limit(api_key, cooldown_seconds=20)
                continue
        return ""

    async def transcribe_audio(self, audio_path: Path) -> str:
        return await asyncio.to_thread(self._sync_transcribe_audio, audio_path)


groq_service = GroqService()
