import re
import html
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.config import DOWNLOAD_DIR, MAX_VIDEO_SIZE_MB
from bot.services.db import get_user_lang
from bot.locales import get_msg
from bot.utils import extract_urls, format_movie_response, safe_remove
from bot.services.downloader import downloader
from bot.services.ai_service import ai_service
from bot.services.tmdb_service import tmdb_service
from bot.keyboards.inline import get_movie_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def safe_edit_text(message: Optional[Message], text: str, reply_markup=None) -> Optional[Message]:
    """Safely edits text message without crashing if message was already modified or deleted."""
    if not message:
        return None
    try:
        return await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        return message


async def process_and_send_result(
    bot: Bot,
    message: Message,
    ai_data: Optional[Dict[str, Any]],
    status_msg: Optional[Message] = None,
    lang: str = "uz"
):
    """Formats AI and TMDb results and sends response with poster and buttons."""
    try:
        if not ai_data or not ai_data.get("found"):
            reason = ai_data.get("reason", "Film aniqlanmadi.") if ai_data else "Error"
            fail_text = get_msg(lang, "error_not_found", reason=html.escape(str(reason)))
            if status_msg:
                await safe_edit_text(status_msg, fail_text)
            else:
                await message.answer(fail_text, parse_mode="HTML")
            return

        # Fetch extra metadata from TMDb
        if status_msg:
            await safe_edit_text(status_msg, get_msg(lang, "status_db"))

        query_title = ai_data.get("title_original") or ai_data.get("title_ru") or ai_data.get("title_uz")
        release_year = str(ai_data.get("release_year") or "")
        tmdb_data = await tmdb_service.search_media(query_title, year=release_year)

        # Format final message and localized keyboard (safe 1000 char max for photo captions)
        formatted_caption = format_movie_response(ai_data, tmdb_data, lang=lang, max_len=1000)
        reply_markup = get_movie_keyboard(ai_data, tmdb_data, lang=lang)

        poster_url = tmdb_data.get("poster_url") if tmdb_data else None

        if poster_url:
            try:
                if status_msg:
                    await status_msg.delete()
                await message.answer_photo(
                    photo=poster_url,
                    caption=formatted_caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                return
            except Exception as e:
                logger.warning(f"[Photo Send Warning] Poster yuborishda xatolik: {e}")

        # If no poster or send failed, send text message
        if status_msg:
            await safe_edit_text(status_msg, formatted_caption, reply_markup=reply_markup)
        else:
            await message.answer(formatted_caption, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e:
        logger.error(f"[Process Error] Xatolik: {e}")
        error_msg = get_msg(lang, "error_general")
        if status_msg:
            try:
                await safe_edit_text(status_msg, error_msg)
            except Exception:
                await message.answer(error_msg, parse_mode="HTML")
        else:
            await message.answer(error_msg, parse_mode="HTML")


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    """Handles screenshots or photos from movies."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    if not message.photo:
        return

    status_msg = await message.answer(get_msg(lang, "status_photo_search"), parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    photo = message.photo[-1]
    unique_id = uuid.uuid4().hex[:12]
    photo_path = DOWNLOAD_DIR / f"photo_{unique_id}.jpg"

    try:
        file_info = await bot.get_file(photo.file_id)
        await bot.download_file(file_info.file_path, destination=photo_path)

        caption_text = message.caption or ""
        ai_data = await ai_service.analyze_image(photo_path, caption=caption_text, lang=lang)

        await process_and_send_result(
            bot=bot,
            message=message,
            ai_data=ai_data,
            status_msg=status_msg,
            lang=lang
        )

    except Exception as e:
        logger.error(f"[Photo Handler Error] {e}")
        await safe_edit_text(status_msg, get_msg(lang, "error_general"))
    finally:
        safe_remove(photo_path)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot):
    """Handles text: either video URLs (Reels/Shorts) or plot description queries (ignores slash commands)."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    text = message.text.strip()

    # 1. Check if message contains URLs
    urls = extract_urls(text)

    if urls:
        url = urls[0]
        status_msg = await message.answer(get_msg(lang, "status_downloading"), parse_mode="HTML")
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        download_result = await downloader.download_video_from_url(url)

        if not download_result or not download_result.get("file_path"):
            # Smart fallback: if user included text/hashtags, try searching by text
            cleaned_prompt = re.sub(r'https?:\/\/\S+', '', text).strip()
            if len(cleaned_prompt) > 4:
                await safe_edit_text(status_msg, get_msg(lang, "status_plot_search"))
                ai_data = await ai_service.analyze_plot_text(cleaned_prompt, lang=lang)
                if ai_data and ai_data.get("found"):
                    await process_and_send_result(bot=bot, message=message, ai_data=ai_data, status_msg=status_msg, lang=lang)
                    return

            fail_text = get_msg(lang, "error_download")
            await safe_edit_text(status_msg, fail_text)
            return

        file_path = download_result["file_path"]
        is_fallback_img = download_result.get("is_image_fallback", False)
        meta_text = f"Title: {download_result.get('title', '')}\nDescription: {download_result.get('description', '')}"

        try:
            if is_fallback_img:
                await safe_edit_text(status_msg, get_msg(lang, "status_photo_search"))
                ai_data = await ai_service.analyze_image(file_path, caption=meta_text, lang=lang)
            else:
                await safe_edit_text(status_msg, get_msg(lang, "status_analyzing"))
                ai_data = await ai_service.analyze_video(file_path, metadata_text=meta_text, lang=lang)

            await process_and_send_result(bot=bot, message=message, ai_data=ai_data, status_msg=status_msg, lang=lang)
        finally:
            safe_remove(file_path)
        return

    # 2. If no URL and length is too short
    if len(text) < 3:
        await message.answer(get_msg(lang, "send_prompt"), parse_mode="HTML")
        return

    # 3. Text Plot Search ("Kino nomini unutdim")
    status_msg = await message.answer(get_msg(lang, "status_plot_search"), parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    ai_data = await ai_service.analyze_plot_text(text, lang=lang)
    await process_and_send_result(
        bot=bot,
        message=message,
        ai_data=ai_data,
        status_msg=status_msg,
        lang=lang
    )


@router.message(F.video | F.video_note | F.animation | F.document)
async def handle_direct_video(message: Message, bot: Bot):
    """Handles directly uploaded video files or video notes."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    video_obj = message.video or message.video_note or message.animation or message.document
    if not video_obj:
        return

    if hasattr(video_obj, "file_size") and video_obj.file_size:
        size_mb = video_obj.file_size / (1024 * 1024)
        if size_mb > MAX_VIDEO_SIZE_MB:
            await message.answer(
                f"⚠️ Video hajmi katta ({size_mb:.1f} MB). Maksimal: {MAX_VIDEO_SIZE_MB} MB.",
                parse_mode="HTML"
            )
            return

    status_msg = await message.answer(get_msg(lang, "status_downloading"), parse_mode="HTML")
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    unique_id = uuid.uuid4().hex[:12]
    ext = ".mp4"
    dest_path = DOWNLOAD_DIR / f"direct_{unique_id}{ext}"

    try:
        file_info = await bot.get_file(video_obj.file_id)
        await bot.download_file(file_info.file_path, destination=dest_path)

        caption_text = message.caption or ""
        await safe_edit_text(status_msg, get_msg(lang, "status_analyzing"))
        ai_data = await ai_service.analyze_video(dest_path, metadata_text=caption_text, lang=lang)

        await process_and_send_result(
            bot=bot,
            message=message,
            ai_data=ai_data,
            status_msg=status_msg,
            lang=lang
        )

    except Exception as e:
        logger.error(f"[Direct Video Error] {e}")
        await safe_edit_text(status_msg, get_msg(lang, "error_general"))
    finally:
        safe_remove(dest_path)


@router.callback_query(F.data.startswith("sim:") | F.data.startswith("similar:"))
async def cb_similar_movies(callback: CallbackQuery, bot: Bot):
    """Generates and displays 3 similar movie recommendations."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    
    title = callback.data.split(":", 1)[1]
    try:
        await callback.answer(get_msg(lang, "status_similar_search"), show_alert=False)
    except Exception:
        pass

    status_msg = await callback.message.reply(get_msg(lang, "status_similar_search"), parse_mode="HTML")
    await bot.send_chat_action(chat_id=callback.message.chat.id, action=ChatAction.TYPING)

    recommendations = await ai_service.get_similar_movies(title, lang=lang)

    if not recommendations:
        await safe_edit_text(status_msg, get_msg(lang, "error_not_found", reason="O'xshash filmlar topilmadi."))
        return

    lines = [f"🎭 <b>'{html.escape(title)}'</b> filmiga o'xshash eng yaxshi filmlar:\n"]
    for idx, rec in enumerate(recommendations[:3], 1):
        m_title = html.escape(str(rec.get("title", "")))
        m_year = html.escape(str(rec.get("year", "")))
        m_genre = html.escape(str(rec.get("genres", "")))
        m_reason = html.escape(str(rec.get("reason", "")))

        lines.append(f"<b>{idx}. {m_title} ({m_year})</b>")
        if m_genre:
            lines.append(f"🎭 <i>Janr: {m_genre}</i>")
        if m_reason:
            lines.append(f"💡 <i>{m_reason}</i>")
        lines.append("")

    lines.append("🍿 <i>Yoqimli tomosha tilaymiz!</i>")
    await safe_edit_text(status_msg, "\n".join(lines))
