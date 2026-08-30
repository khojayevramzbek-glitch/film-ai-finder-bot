import json
import random
import asyncio
import logging
from typing import Dict, Any, Optional, List

from bot.config import GROQ_API_KEYS
from bot.services.key_manager import APIKeyPool

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
    """Ultra-fast Groq LPU inference engine for AI Movie Curator and Quizzes."""

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
                                {"role": "system", "content": "You are a professional cinema AI curator and movie trivia expert. Always return responses in valid clean JSON format only."},
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


groq_service = GroqService()
