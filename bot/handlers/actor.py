import html
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatAction

from bot.services.db import get_user_lang, is_user_banned
from bot.services.groq_service import groq_service
from bot.services.tmdb_service import tmdb_service
from bot.services.subscription import check_user_subscription, get_subscription_keyboard
from bot.locales import get_msg
from bot.keyboards.inline import get_actor_filmography_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def process_actor_search(message: Message, bot: Bot, query: str, lang: str = "uz"):
    """Processes actor/director filmography search and sends rich profile card."""
    user_id = message.from_user.id if message.from_user else 0
    if is_user_banned(user_id):
        return

    is_sub, missing = await check_user_subscription(bot, user_id)
    if not is_sub:
        await message.answer(get_msg(lang, "sub_required"), reply_markup=get_subscription_keyboard(missing, lang), parse_mode="HTML")
        return

    status_msg = await message.answer("🎭 <b>Aktyor / Rejissyor ma'lumotlari yuklanmoqda...</b>", parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # 1. Fetch AI filmography via Groq
    actor_data = await groq_service.get_actor_filmography(query, lang=lang)

    if not actor_data or not actor_data.get("person_name"):
        await status_msg.edit_text("😔 <b>Aktyor yoki rejissyor topilmadi.</b>\n\nIltimos, ismini to'g'ri yozib qayta urinib ko'ring (masalan: <i>/actor Leonardo DiCaprio</i>).", parse_mode="HTML")
        return

    person_name = html.escape(str(actor_data.get("person_name", query)))
    role = html.escape(str(actor_data.get("role", "Kino Ijodkori")))
    bio = html.escape(str(actor_data.get("bio", "")))
    top_movies = actor_data.get("top_movies", [])

    # 2. Fetch actor profile photo from TMDb
    tmdb_person = await tmdb_service.search_person(person_name)
    photo_url = tmdb_person.get("profile_url") if tmdb_person else None

    # Format beautiful text card
    lines = [
        f"⭐️ <b>{person_name}</b>",
        f"🎭 <b>Kasbi:</b> {role}\n",
        f"📖 <i>{bio}</i>\n",
        "━━━━━━━━━━━━━━━━━━━━━━━",
        "🎬 <b>ENG ENG SARA TOP-5 TA DURDONA FILMLARI:</b>\n"
    ]

    for idx, m in enumerate(top_movies[:5], 1):
        m_title = html.escape(str(m.get("title", "")))
        m_year = html.escape(str(m.get("year", "")))
        m_rating = html.escape(str(m.get("rating", "")))
        m_role = html.escape(str(m.get("role_name", "")))
        m_desc = html.escape(str(m.get("description", "")))

        role_str = f" — <i>(Roli: {m_role})</i>" if m_role else ""
        lines.append(f"<b>{idx}. {m_title} ({m_year})</b> — ⭐️ {m_rating}{role_str}")
        if m_desc:
            lines.append(f"   💡 <i>{m_desc}</i>")
        lines.append("")

    lines.append("🍿 <i>Tomosha qilish uchun pastdagi tugmalardan birini tanlang:</i>")
    formatted_text = "\n".join(lines)

    reply_markup = get_actor_filmography_keyboard(person_name, top_movies, lang=lang)

    if photo_url:
        try:
            await status_msg.delete()
            await message.answer_photo(
                photo=photo_url,
                caption=formatted_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            return
        except Exception:
            pass

    await status_msg.edit_text(formatted_text, reply_markup=reply_markup, parse_mode="HTML")


@router.message(Command("actor"))
@router.message(Command("director"))
async def cmd_actor(message: Message, bot: Bot):
    """Handles /actor and /director command."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    args = message.text.replace("/actor", "").replace("/director", "").strip()
    if not args:
        await message.answer(
            "🎭 <b>Aktyor yoki Rejissyor bo'yicha qidirish:</b>\n\n"
            "Ismni buyruq bilan birga yozing:\n"
            "👉 <code>/actor Leonardo DiCaprio</code>\n"
            "👉 <code>/actor Christopher Nolan</code>\n"
            "👉 <code>/actor Tom Cruise</code>\n"
            "👉 <code>/actor Jackie Chan</code>",
            parse_mode="HTML"
        )
        return

    await process_actor_search(message=message, bot=bot, query=args, lang=lang)
