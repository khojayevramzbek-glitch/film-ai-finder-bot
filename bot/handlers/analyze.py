import uuid
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ChatAction

from bot.config import DOWNLOAD_DIR, MAX_VIDEO_SIZE_MB
from bot.services.db import get_user_lang
from bot.locales import get_msg
from bot.utils import extract_urls, format_movie_response, safe_remove
from bot.services.downloader import downloader
from bot.services.ai_service import ai_service
from bot.services.tmdb_service import tmdb_service
from bot.keyboards.inline import get_movie_keyboard

router = Router()


async def process_video_analysis(bot: Bot, message: Message, video_path: Path, metadata_text: str = "", status_msg: Message = None, lang: str = "uz"):
    """Core function to process AI analysis and return localized formatted results."""
    try:
        if status_msg:
            await status_msg.edit_text(get_msg(lang, "status_analyzing"), parse_mode="HTML")

        # Send typing action
        await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

        # AI Recognition in user's language
        ai_data = await ai_service.analyze_video(video_path, metadata_text=metadata_text, lang=lang)

        if not ai_data or not ai_data.get("found"):
            reason = ai_data.get("reason", "Video lavhasi aniqlanmadi.") if ai_data else "Error"
            fail_text = get_msg(lang, "error_not_found", reason=reason)
            if status_msg:
                await status_msg.edit_text(fail_text, parse_mode="HTML")
            else:
                await message.answer(fail_text, parse_mode="HTML")
            return

        # Fetch extra metadata from TMDb
        if status_msg:
            await status_msg.edit_text(get_msg(lang, "status_db"), parse_mode="HTML")

        query_title = ai_data.get("title_original") or ai_data.get("title_ru") or ai_data.get("title_uz")
        release_year = str(ai_data.get("release_year") or "")
        tmdb_data = await tmdb_service.search_media(query_title, year=release_year)

        # Format final message and localized keyboard
        formatted_caption = format_movie_response(ai_data, tmdb_data, lang=lang)
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
                print(f"[Photo Send Warning] Poster yuborishda xatolik: {e}")

        # If no poster, send text message
        if status_msg:
            await status_msg.edit_text(formatted_caption, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await message.answer(formatted_caption, reply_markup=reply_markup, parse_mode="HTML")

    except Exception as e:
        print(f"[Process Error] Umumiy xatolik: {e}")
        error_msg = get_msg(lang, "error_general")
        if status_msg:
            try:
                await status_msg.edit_text(error_msg, parse_mode="HTML")
            except Exception:
                await message.answer(error_msg, parse_mode="HTML")
        else:
            await message.answer(error_msg, parse_mode="HTML")

    finally:
        safe_remove(video_path)


@router.message(F.text)
async def handle_text_url(message: Message, bot: Bot):
    """Handles text messages containing video URLs in user's language."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    urls = extract_urls(message.text)
    if not urls:
        await message.answer(get_msg(lang, "send_prompt"), parse_mode="HTML")
        return

    url = urls[0]
    is_tiktok = "tiktok.com" in url.lower()

    status_msg = await message.answer(get_msg(lang, "status_downloading"), parse_mode="HTML")

    download_result = await downloader.download_video_from_url(url)

    if not download_result or not download_result.get("file_path"):
        fail_text = get_msg(lang, "error_tiktok") if is_tiktok else get_msg(lang, "error_download")
        await status_msg.edit_text(fail_text, parse_mode="HTML")
        return

    video_path = download_result["file_path"]
    meta_text = f"Title: {download_result.get('title', '')}\nDescription: {download_result.get('description', '')}"

    await process_video_analysis(
        bot=bot,
        message=message,
        video_path=video_path,
        metadata_text=meta_text,
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
                f"⚠️ Video hajmi juda katta ({size_mb:.1f} MB). Maksimal: {MAX_VIDEO_SIZE_MB} MB.",
                parse_mode="HTML"
            )
            return

    status_msg = await message.answer(get_msg(lang, "status_downloading"), parse_mode="HTML")

    unique_id = uuid.uuid4().hex[:12]
    ext = ".mp4"
    dest_path = DOWNLOAD_DIR / f"direct_{unique_id}{ext}"

    try:
        file_info = await bot.get_file(video_obj.file_id)
        await bot.download_file(file_info.file_path, destination=dest_path)

        caption_text = message.caption or ""
        await process_video_analysis(
            bot=bot,
            message=message,
            video_path=dest_path,
            metadata_text=caption_text,
            status_msg=status_msg,
            lang=lang
        )

    except Exception as e:
        print(f"[Direct Video Error] Yuklashda xatolik: {e}")
        safe_remove(dest_path)
        await status_msg.edit_text(get_msg(lang, "error_general"), parse_mode="HTML")
