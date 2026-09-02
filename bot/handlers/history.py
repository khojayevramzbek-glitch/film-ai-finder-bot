import html
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from bot.services.db import (
    get_user_lang,
    get_user_search_history,
    get_user_referral_stats,
    get_top_referrers
)

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("history"))
async def cmd_search_history(message: Message):
    """Shows user's recent successfully identified movies."""
    user_id = message.from_user.id if message.from_user else 0
    history = get_user_search_history(user_id, limit=8)

    if not history:
        text = (
            "📂 <b>SIZNING QIDIRUV TARIXINGIZ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>Hozircha muvaffaqiyatli qidiruvlaringiz mavjud emas.</i>\n\n"
            "Instagram/YouTube havolasi, rasm yoki kino syujetini yuboring — bot darhol topib, tarixingizga qo'shadi!"
        )
        await message.answer(text, parse_mode="HTML")
        return

    lines = [
        "📂 <b>SIZNING OXIRGI TOPILGAN FILMLARINGIZ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    for idx, item in enumerate(history, 1):
        m_title = html.escape(item.get("found_title") or "Noma'lum film")
        s_type = item.get("search_type", "qidiruv").title()
        date_str = str(item.get("created_at", ""))[:16]
        lines.append(f"<b>{idx}. {m_title}</b>\n   └ <i>Tur: {s_type} | Sana: {date_str}</i>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <i>Sevimli kinolaringizni /saved orqali saqlab qo'yishingiz mumkin.</i>")

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Saqlangan Kinolar (/saved)", callback_data="btn_saved")],
        [InlineKeyboardButton(text="🎲 Yangi Kino Tanlash (/random)", callback_data="rand_menu")]
    ])
    await message.answer("\n".join(lines), reply_markup=buttons, parse_mode="HTML")


@router.callback_query(F.data == "btn_history")
async def cb_btn_history(callback: CallbackQuery):
    """Callback trigger for history."""
    await cmd_search_history(callback.message)
    await callback.answer()


@router.callback_query(F.data == "btn_invite")
async def cb_btn_invite(callback: CallbackQuery):
    """Callback trigger for referral invite."""
    await cmd_referral(callback.message)
    await callback.answer()


@router.message(Command("invite"))
@router.message(Command("referral"))
async def cmd_referral(message: Message):
    """Generates personal viral referral invite link and shows bonus points."""
    user_id = message.from_user.id if message.from_user else 0
    stats = get_user_referral_stats(user_id)
    ref_count = stats.get("referral_count", 0)
    points = stats.get("points", 0)

    bot_username = "FilmAiFinderbot"
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_text = (
        "🎬 Men kinolarni Instagram reels, rasm yoki syujetidan darhol topib beradigan "
        "eng zo'r Sun'iy Intellekt botini topdim! Sen ham sinab ko'r: " + ref_link
    )
    import urllib.parse
    telegram_share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote('🎬 Kinolarni AI orqali topuvchi super bot!')}"

    text = (
        "👥 <b>DO'STLARNI TAKLIF QILING VA BALL YIG'ING!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Botingizni do'stlaringizga ulashing va har bir taklif qilingan do'stingiz uchun <b>+50 ball</b> oling!\n\n"
        f"🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📊 <b>Sizning natijalaringiz:</b>\n"
        f"  • Taklif qilingan do'stlar: <b>{ref_count} ta</b>\n"
        f"  • Jami to'plangan ballaringiz: <b>{points} ball</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Do'stlarga Ulashish", url=telegram_share_url)],
        [InlineKeyboardButton(text="🏆 TOP Taklif Qilganlar", callback_data="ref_leaderboard")]
    ])
    await message.answer(text, reply_markup=buttons, parse_mode="HTML", disable_web_page_preview=True)


@router.callback_query(F.data == "ref_leaderboard")
async def cb_referral_leaderboard(callback: CallbackQuery):
    """Renders leaderboard of top referrers."""
    top_users = get_top_referrers(limit=10)
    if not top_users:
        await callback.answer("Hozircha taklif qilganlar reytingi shakllanmagan.", show_alert=True)
        return

    lines = [
        "🏆 <b>ENG KO'P DO'STINI TAKLIF QILGANLAR (TOP-10)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for idx, u in enumerate(top_users):
        medal = medals[idx] if idx < len(medals) else "👤"
        name = html.escape(u.get("first_name") or u.get("username") or f"ID {u['user_id']}")
        cnt = u.get("invite_count", 0)
        pts = u.get("points", 0)
        lines.append(f"{medal} <b>{name}</b> — <b>{cnt} ta do'st</b> (<code>{pts} ball</code>)")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🎁 <i>Reytingda yuqori o'rinni olganlar doimiy sovg'alarga ega bo'ladi!</i>")

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="ref_back")]
    ])
    try:
        await callback.message.edit_text("\n".join(lines), reply_markup=buttons, parse_mode="HTML")
    except Exception:
        await callback.message.answer("\n".join(lines), reply_markup=buttons, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "ref_back")
async def cb_referral_back(callback: CallbackQuery):
    """Returns to referral screen."""
    user_id = callback.from_user.id if callback.from_user else 0
    stats = get_user_referral_stats(user_id)
    ref_count = stats.get("referral_count", 0)
    points = stats.get("points", 0)
    ref_link = f"https://t.me/FilmAiFinderbot?start=ref_{user_id}"

    import urllib.parse
    telegram_share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote('🎬 Kinolarni AI orqali topuvchi super bot!')}"

    text = (
        "👥 <b>DO'STLARNI TAKLIF QILING VA BALL YIG'ING!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📊 <b>Sizning natijalaringiz:</b>\n"
        f"  • Taklif qilingan do'stlar: <b>{ref_count} ta</b>\n"
        f"  • Jami to'plangan ballaringiz: <b>{points} ball</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Do'stlarga Ulashish", url=telegram_share_url)],
        [InlineKeyboardButton(text="🏆 TOP Taklif Qilganlar", callback_data="ref_leaderboard")]
    ])
    try:
        await callback.message.edit_text(text, reply_markup=buttons, parse_mode="HTML", disable_web_page_preview=True)
    except Exception:
        pass
    await callback.answer()
