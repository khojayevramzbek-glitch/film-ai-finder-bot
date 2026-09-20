import re
from html import escape
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.enums import ChatType
from group_bot.database import get_rules, set_rules
from .moderation import is_admin_or_allowed

router = Router()

RULES_REGEX = re.compile(r"^/?(rules|qoidalar|правила)$", re.IGNORECASE)

DEFAULT_RULES = (
    "📌 <b>GURUH QOIDALARI:</b>\n"
    "1. ❌ <b>Haqorat</b> (so‘z, stiker, GIF, emoji) — 1 daq mute\n"
    "2. ❌ <b>Spam / flood</b> (ketma-ket xabar, stiker, GIF) — 1 daq mute\n"
    "3. ❌ <b>Reklama</b> (ruxsatsiz reklama/havola) — 1 daq mute\n"
    "4. ❌ <b>Janjal / provokatsiya</b> (tortishuv chiqarish) — 1 daq mute\n"
    "5. ❌ <b>Keraksiz xabarlar</b> (mazmunsiz/offtop) — 1 daq mute\n"
    "6. ❌ <b>Adminga qarshilik</b> (qasddan bo‘ysunmaslik) — 1 daq mute\n"
    "7. 📊 <b>СТАТА</b> — haftalik TOP 1 ga 1 hafta Admin (sun’iy oshirilsa — mute va bekor)\n"
    "8. ⚠️ <b>Takroriy qoidabuzarlik</b> — mute vaqti oshiriladi\n"
    "—\n"
    "🤝 <i>Hurmat saqlaymiz. Har bir qoidabuzarlik = kamida 1 daqiqa mute.</i>"
)


@router.message(Command("setrules"))
async def cmd_setrules(message: types.Message, bot: Bot):
    if message.chat.type in [ChatType.PRIVATE, ChatType.CHANNEL]:
        return

    if not await is_admin_or_allowed(message.chat.id, message.from_user, bot):
        return

    # /setrules dan keyingi matnni olish
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.reply(
            "❗ Yangi qoidalarni kiritish uchun: <code>/setrules &lt;qoidalar matni&gt;</code> deb yozing.",
            parse_mode="HTML"
        )
        return

    new_rules = args[1].strip()
    set_rules(message.chat.id, new_rules)
    await message.reply("✅ <b>Guruh qoidalari muvaffaqiyatli yangilandi va saqlandi!</b>", parse_mode="HTML")


@router.message(lambda msg: bool(RULES_REGEX.match((msg.text or msg.caption or "").strip())))
async def check_rules_command(message: types.Message):
    text = (message.text or message.caption or "").strip()

    if RULES_REGEX.match(text):
        custom_rules = get_rules(message.chat.id)
        if custom_rules:
            response = f"<b>📜 Guruh Qoidalari:</b>\n\n{escape(custom_rules)}"
        else:
            response = DEFAULT_RULES

        await message.reply(response, parse_mode="HTML", disable_notification=True)
