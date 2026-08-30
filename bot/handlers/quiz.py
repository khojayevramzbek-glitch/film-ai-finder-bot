import html
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.services.db import get_user_lang, add_user_points, get_user_points, get_quiz_leaderboard
from bot.locales import get_msg
from bot.services.ai_service import ai_service
from bot.keyboards.inline import get_quiz_keyboard, get_quiz_result_keyboard

router = Router()


async def send_new_quiz(bot: Bot, chat_id: int, user_id: int, status_msg: Message = None, lang: str = "uz"):
    """Generates and sends a fresh AI movie trivia question."""
    if not status_msg:
        status_msg = await bot.send_message(chat_id, "🎲 <b>AI Kino Viktorinasi tayyorlanmoqda...</b>", parse_mode="HTML")
    else:
        try:
            await status_msg.edit_text("🎲 <b>AI Yangi savol tayyorlamoqda...</b>", parse_mode="HTML")
        except Exception:
            pass

    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    quiz_data = await ai_service.generate_quiz(lang=lang)

    if not quiz_data or "question" not in quiz_data or "options" not in quiz_data:
        try:
            await status_msg.edit_text("❌ Savol tayyorlashda xatolik. Qayta urinib ko'ring: /quiz", parse_mode="HTML")
        except Exception:
            pass
        return

    question = html.escape(str(quiz_data.get("question", "")))
    options = quiz_data.get("options", [])
    correct_idx = int(quiz_data.get("correct_index", 0))
    explanation = html.escape(str(quiz_data.get("explanation", "")))

    user_score = get_user_points(user_id)

    formatted_text = (
        f"🎮 <b>AI KINO VIKTORINASI</b>\n"
        f"⭐️ <i>Sizning jami ballingiz: {user_score} ball</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"❓ <b>{question}</b>\n\n"
        "<i>To'g'ri javobni tanlang:</i>"
    )

    reply_markup = get_quiz_keyboard(options, correct_idx)

    # Store explanation temporarily in callback context or direct rendering
    try:
        await status_msg.edit_text(formatted_text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await bot.send_message(chat_id, formatted_text, reply_markup=reply_markup, parse_mode="HTML")


@router.message(Command("quiz"))
@router.message(Command("game"))
async def cmd_quiz(message: Message, bot: Bot):
    """Starts AI movie quiz."""
    user_id = message.from_user.id if message.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    await send_new_quiz(bot=bot, chat_id=message.chat.id, user_id=user_id, lang=lang)


@router.callback_query(F.data.startswith("quiz_ans:"))
async def cb_quiz_answer(callback: CallbackQuery):
    """Handles answer selection."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"

    parts = callback.data.split(":")
    selected_idx = int(parts[1])
    correct_idx = int(parts[2])

    is_correct = selected_idx == correct_idx

    if is_correct:
        add_user_points(user_id, 10)
        await callback.answer("🎉 To'g'ri javob! +10 ball", show_alert=False)
    else:
        await callback.answer("❌ Noto'g'ri javob!", show_alert=False)

    user_score = get_user_points(user_id)

    if is_correct:
        res_text = (
            f"🎉 <b>BARAKALLA, TO'G'RI JAVOB! (+10 Ball)</b>\n\n"
            f"⭐️ <i>Sizning jami ballingiz: {user_score} ball</i>"
        )
    else:
        labels = ["A", "B", "C", "D"]
        correct_letter = labels[correct_idx] if correct_idx < len(labels) else ""
        res_text = (
            f"❌ <b>Afsus, noto'g'ri javob!</b>\n\n"
            f"✅ <b>To'g'ri javob varianti:</b> {correct_letter}\n"
            f"⭐️ <i>Sizning jami ballingiz: {user_score} ball</i>"
        )

    try:
        await callback.message.edit_text(res_text, reply_markup=get_quiz_result_keyboard(lang), parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "quiz_next")
async def cb_quiz_next(callback: CallbackQuery, bot: Bot):
    """Loads next question."""
    user_id = callback.from_user.id if callback.from_user else 0
    lang = get_user_lang(user_id) or "uz"
    await send_new_quiz(bot=bot, chat_id=callback.message.chat.id, user_id=user_id, status_msg=callback.message, lang=lang)
    await callback.answer()


@router.callback_query(F.data == "quiz_top")
async def cb_quiz_top(callback: CallbackQuery):
    """Displays TOP players leaderboard."""
    top_players = get_quiz_leaderboard(limit=10)
    lines = [
        "🏆 <b>AI KINO VIKTORINASI — TOP O'YINCHILAR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    if not top_players:
        lines.append("<i>Hozircha o'yinchilar yo'q. Birinchi bo'lib ball to'plang!</i>")
    else:
        for idx, p in enumerate(top_players, 1):
            badge = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            lines.append(f"{badge} ID: <code>{p['user_id']}</code> — <b>{p['points']} ball</b>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🎮 <i>O'ynashda davom eting va 1-o'ringa chiqing!</i>")

    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=get_quiz_result_keyboard(), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()
