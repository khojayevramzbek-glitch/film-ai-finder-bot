import html
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.services.db import get_user_lang, is_user_banned
from bot.services.characters import CHARACTERS, get_character_info
from bot.services.groq_service import groq_service
from bot.services.subscription import check_user_subscription, get_subscription_keyboard
from bot.locales import get_msg
from bot.keyboards.inline import get_characters_keyboard, get_character_chat_keyboard

logger = logging.getLogger(__name__)
router = Router()


class CharacterSessionState(StatesGroup):
    chatting = State()


@router.message(Command("character"))
@router.message(Command("persona"))
@router.message(Command("heroes"))
async def cmd_character_menu(message: Message, state: FSMContext, bot: Bot):
    """Opens character selection menu."""
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    if is_user_banned(user_id):
        return

    lang = get_user_lang(user_id) or "uz"

    is_sub, missing = await check_user_subscription(bot, user_id)
    if not is_sub:
        await message.answer(get_msg(lang, "sub_required"), reply_markup=get_subscription_keyboard(missing, lang), parse_mode="HTML")
        return

    text = (
        "🎭 <b>KINO QAHRAMONLARI BILAN JONLI SUHBAT!</b>\n\n"
        "Quyidagi afsonaviy kino qahramonlaridan birini tanlang va u bilan jonli, samimiy va qiziqarli suhbat quring:\n\n"
        "<i>(Qahramonlar o'z xarakteri va fe'l-atvori bilan javob berishadi)</i>"
    )
    await message.answer(text, reply_markup=get_characters_keyboard(lang), parse_mode="HTML")


@router.callback_query(F.data.startswith("char_sel:"))
async def cb_select_character(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Starts roleplay session with the selected character."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    char_id = callback.data.split(":")[1]
    char_info = get_character_info(char_id)

    # Set FSM state
    await state.set_state(CharacterSessionState.chatting)
    await state.update_data(
        character_id=char_id,
        history=[]
    )

    greeting = char_info["greeting"].get(lang, char_info["greeting"]["uz"])
    header = f"<b>{char_info['avatar_title']}</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    await callback.message.edit_text(
        header + greeting,
        reply_markup=get_character_chat_keyboard(lang),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(StateFilter(CharacterSessionState.chatting), F.text & ~F.text.startswith("/"))
async def handle_character_message(message: Message, state: FSMContext, bot: Bot):
    """Handles continuous roleplay dialogue."""
    user_id = message.from_user.id if message.from_user else 0
    if is_user_banned(user_id):
        return

    lang = get_user_lang(user_id) or "uz"
    data = await state.get_data()
    char_id = data.get("character_id", "joker")
    history = data.get("history", [])

    char_info = get_character_info(char_id)

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Generate response via Groq LPU
    user_text = message.text.strip()
    reply_text = await groq_service.chat_with_character(
        character_id=char_id,
        user_message=user_text,
        chat_history=history,
        lang=lang
    )

    # Update conversation history
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": reply_text})
    await state.update_data(history=history[-8:])

    formatted_reply = (
        f"<b>{char_info['emoji']} {char_info['name']}:</b>\n\n"
        f"{html.escape(reply_text)}"
    )

    await message.answer(
        formatted_reply,
        reply_markup=get_character_chat_keyboard(lang),
        parse_mode="HTML"
    )


@router.message(StateFilter(CharacterSessionState.chatting), F.voice)
async def handle_character_voice(message: Message, state: FSMContext, bot: Bot):
    """Handles voice note roleplay dialogue using Whisper Turbo transcription."""
    user_id = message.from_user.id if message.from_user else 0
    if is_user_banned(user_id):
        return

    lang = get_user_lang(user_id) or "uz"
    data = await state.get_data()
    char_id = data.get("character_id", "joker")
    history = data.get("history", [])
    char_info = get_character_info(char_id)

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    from bot.config import DOWNLOAD_DIR
    import uuid
    voice_path = DOWNLOAD_DIR / f"voice_{uuid.uuid4().hex[:8]}.ogg"

    try:
        await bot.download(message.voice, destination=voice_path)
        transcribed_text = await groq_service.transcribe_audio(voice_path)
    except Exception as e:
        logger.warning(f"[Voice Download Error] {e}")
        transcribed_text = ""
    finally:
        if voice_path.exists():
            try:
                voice_path.unlink()
            except Exception:
                pass

    if not transcribed_text:
        await message.answer(
            f"🎙 <b>{char_info['name']}:</b> <i>Ovozingizni yaxshi tushuna olmadim, iltimos, qayta yuboring yoki yozing.</i>",
            reply_markup=get_character_chat_keyboard(lang),
            parse_mode="HTML"
        )
        return

    # Generate reply
    reply_text = await groq_service.chat_with_character(
        character_id=char_id,
        user_message=transcribed_text,
        chat_history=history,
        lang=lang
    )

    history.append({"role": "user", "content": transcribed_text})
    history.append({"role": "assistant", "content": reply_text})
    await state.update_data(history=history[-8:])

    formatted_reply = (
        f"🎙 <i>(Ovozingiz eshitildi: \"{html.escape(transcribed_text)}\")</i>\n\n"
        f"<b>{char_info['emoji']} {char_info['name']}:</b>\n\n"
        f"{html.escape(reply_text)}"
    )

    await message.answer(
        formatted_reply,
        reply_markup=get_character_chat_keyboard(lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "char_change")
async def cb_change_character(callback: CallbackQuery, state: FSMContext):
    """Reopens character selection grid."""
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    text = "🎭 <b>Boshqa qahramonni tanlang:</b>"
    try:
        await callback.message.edit_text(text, reply_markup=get_characters_keyboard(lang), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=get_characters_keyboard(lang), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "char_exit")
@router.message(Command("exit"), StateFilter(CharacterSessionState.chatting))
async def cb_exit_character_chat(event: Message | CallbackQuery, state: FSMContext):
    """Exits character chat mode and returns to normal bot state."""
    await state.clear()
    user_id = event.from_user.id if event.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    exit_text = (
        "🛑 <b>Qahramon bilan suhbat yakunlandi.</b>\n\n"
        "Endi botdan odatiy tarzda foydalanishingiz mumkin: Instagram Reels, YouTube Shorts havolasi, rasm yoki kino nomini yuboring! 🎬🍿"
    )

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(exit_text, parse_mode="HTML")
        except Exception:
            await event.message.answer(exit_text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(exit_text, parse_mode="HTML")
