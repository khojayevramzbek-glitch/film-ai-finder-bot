from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from html import escape

router = Router()

WEBAPP_URL = "https://uchunrisk-film-ai-finder-bot.hf.space/webapp"


def get_main_menu_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Guruhga Qo'shish",
                    url=f"https://t.me/{bot_username}?startgroup=true"
                ),
                InlineKeyboardButton(
                    text="📱 Mini App Boshqaruv",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ],
            [
                InlineKeyboardButton(text="🔘 Bot Holati (On/Off)", callback_data="menu_bot_status"),
                InlineKeyboardButton(text="📋 Barcha Buyruqlar", callback_data="menu_commands"),
            ],
            [
                InlineKeyboardButton(text="🛡 Himoya Tizimlari", callback_data="menu_security"),
                InlineKeyboardButton(text="🤬 So'kinish Filtri", callback_data="menu_censor"),
            ],
            [
                InlineKeyboardButton(text="📊 Guruh Statistikasi", callback_data="menu_stats"),
                InlineKeyboardButton(text="😴 AFK / Sleep Rejimi", callback_data="menu_afk"),
            ],
            [
                InlineKeyboardButton(text="📜 Qoidalar & Sozlash", callback_data="menu_rules"),
                InlineKeyboardButton(text="👑 Bosh Admin", url="https://t.me/khojayev_ramz")
            ]
        ]
    )



def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Asosiy Menyuga Qaytish", callback_data="menu_back")
            ]
        ]
    )


def get_welcome_text(user_full_name: str) -> str:
    return (
        f"🛡 <b>Assalomu alaykum, {escape(user_full_name)}!</b>\n\n"
        "<b>Blizkiy's bot 🔰</b> — Telegram guruhlaringizni 24/7 rejimida tartibda saqlovchi, "
        "spam va toshqinlardan himoya qiluvchi hamda qulay boshqaruvni ta'minlovchi professional robot-moderator!\n\n"
        "✨ <b>Botning Asosiy Imkoniyatlari:</b>\n"
        "├ ⚡️ <b>Aqlli Anti-Flood & Anti-Spam:</b> Ketma-ket yozilgan xabarlar, stiker, GIF va premium emojilar toshqinini darhol o'chiradi va cheklaydi.\n"
        "├ 🤬 <b>So'kinish & Haqorat Filtri:</b> So'kingan a'zolarni 15 soniya mute qiladi, adminlarga esa qat'iy ogohlantirish beradi.\n"
        "├ 🔇 <b>Kuchli Moderatsiya:</b> <code>/mute</code>, <code>/ban</code>, <code>/warn</code> — ham Reply, ham to'g'ridan-to'g'ri <code>@username</code> orqali ishlaydi!\n"
        "├ 😴 <b>AFK / Uyqu Rejimi:</b> Adminlar band bo'lganda (<code>/sleep 1h</code>), ularni chaqirganlarga bot qachon kelishini avtomatik aytadi.\n"
        "├ 📜 <b>Moslashuvchan Qoidalar:</b> Guruh qoidalarini saqlash va ko'rsatish (<code>/rules</code>, <code>/setrules</code>).\n"
        "└ 📊 <b>Guruh Statistikasi:</b> 24 soatlik xabarlar va eng faol a'zolar hisobi.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <b>Botni Guruhingizga Qo'shish:</b>\n"
        "1️⃣ Pastdagi <b>«➕ Guruhga Qo'shish»</b> tugmasini bosing va guruhingizni tanlang.\n"
        "2️⃣ Botga guruhda <b>Administrator</b> huquqlarini bering (xabarlarni o'chirish va a'zolarni cheklash).\n"
        "3️⃣ Tayyor! Bot guruhingizni bir umr xavfsiz himoya qiladi.\n\n"
        "<i>Batafsil ma'lumot olish uchun quyidagi tugmalardan birini tanlang:</i>"
    )


COMMANDS_TEXT = (
    "📋 <b>Barcha Buyruqlar Ro'yxati:</b>\n\n"
    "👮‍♂️ <b>Admin Buyruqlari (Reply yoki @username orqali):</b>\n"
    "• <code>/mute @user 15m</code> — Foydalanuvchini yozishdan cheklash (15m, 2h, 1d)\n"
    "• <code>/unmute @user</code> — Yozish cheklovini olib tashlash\n"
    "• <code>/ban @user</code> — Guruhdan chiqarish va bloklash\n"
    "• <code>/unban @user</code> — Blokdan chiqarish\n"
    "• <code>/warn @user [sabab]</code> — Ogohlantirish berish (3 tasida cheklanadi)\n"
    "• <code>/unwarn @user</code> — Ogohlantirishni bekor qilish\n\n"
    "📊 <b>Statistika (Stata) Buyruqlari:</b>\n"
    "• <code>stata</code> / <code>/stata</code> — Guruh faolligi reytingi (Top aktivlar)\n"
    "• <code>statasi @user</code> — Foydalanuvchi faolligini ko'rish\n"
    "• <code>/stata on</code> / <code>/stata off</code> — Statistikani yoqish yoki o'chirish\n"
    "• <code>/stata public</code> / <code>/stata admin</code> — Ko'rish huquqini sozlash\n\n"
    "🤬 <b>So'kinish Filtri (Censor) Buyruqlari:</b>\n"
    "• <code>/censor on</code> / <code>/censor off</code> — Filtrni yoqish yoki o'chirish\n"
    "• <code>/addbadword &lt;so'z&gt;</code> — Yangi taqiqlangan so'z qo'shish\n"
    "• <code>/delbadword &lt;so'z&gt;</code> — So'zni ro'yxatdan chiqarish\n"
    "• <code>/badwords</code> — Guruhning maxsus taqiqlangan so'zlarini ko'rish\n\n"
    "😴 <b>AFK / Sleep Buyruqlari:</b>\n"
    "• <code>/sleep 1h [sabab]</code> — Uyqu yoki bandlik rejimini yoqish\n"
    "• <code>/wake</code> — Uyqu rejimidan chiqish\n\n"
    "📜 <b>Umumiy Buyruqlar:</b>\n"
    "• <code>/rules</code> — Guruh qoidalarini ko'rish\n"
    "• <code>/setrules [matn]</code> — Yangi qoidalarni kiritish (faqat asosiy adminlar)\n"
    "• <code>/info</code> — Guruh va shaxsiy ID ma'lumotlari\n"
    "• <code>/help</code> — Yordam xabari"
)

STATS_TEXT = (
    "📊 <b>Guruh Statistikasi (Stata) Tizimi:</b>\n\n"
    "Guruhdagi 24 soatlik xabarlarni va eng faol a'zolar (Top aktivlar) reytingini aniq hisoblab boruvchi aqlli tizim!\n\n"
    "📌 <b>Asosiy Buyruqlar:</b>\n"
    "• <code>stata</code> yoki <code>/stata</code> — Guruhning 24 soatlik Top faol a'zolari reytingini ko'rish (medallar bilan)\n"
    "• <code>statasi @username</code> — Bitta foydalanuvchining so'nggi 24 soatdagi xabarlar sonini bilish (Reply yoki tag orqali)\n\n"
    "⚙️ <b>Admin Sozlamalari (Yoqish / O'chirish):</b>\n"
    "• <code>/stata on</code> — Guruhda statistikani yoqish\n"
    "• <code>/stata off</code> — Guruhda statistikani o'chirish\n"
    "• <code>/stata public</code> — Statistikani barcha a'zolar ko'rishi uchun ochish\n"
    "• <code>/stata admin</code> — Statistikani faqat adminlar ko'rishi uchun cheklash\n\n"
    "💡 <i>Anti-flood tizimi tozalagan barcha nojo'ya va spam xabarlar hisobga olinmaydi — faqat haqiqiy va toza xabarlar sanaladi!</i>"
)

SECURITY_TEXT = (
    "🛡 <b>Aqlli Himoya Tizimlari (Anti-Flood & Anti-Spam):</b>\n\n"
    "Botingiz guruhni quyidagi nojo'ya harakatlardan 24/7 avtomatik himoya qiladi:\n\n"
    "1️⃣ <b>Stiker va GIF Toshqini:</b>\n"
    "Foydalanuvchi 4 soniya ichida 2 tadan ortiq stiker yoki GIF yuborsa, bot xabarlarni darhol o'chiradi va 1 daqiqaga mute beradi.\n\n"
    "2️⃣ <b>Ketma-ket Bo'lak Xabarlar (Piece Flood):</b>\n"
    "Guruhda tez-tez qisqa-qisqa so'zlar (masalan: <i>'salom'</i>, <i>'qales'</i>, <i>'yaxshimisz'</i>) yozib chatni to'ldiruvchilarning xabarlari tozalanadi.\n\n"
    "3️⃣ <b>Katta Matnlar (Offtop spam):</b>\n"
    "Ekranni egallab oluvchi ko'p qatorli keraksiz matnlar zudlik bilan nazoratga olinadi.\n\n"
    "4️⃣ <b>Adminlar Uchun Himoya:</b>\n"
    "Adminlar guruhda bemalol boshqaruv olib borishlari uchun ularga nisbatan cheklovlar qo'llanmaydi, lekin nojo'ya flood bo'lsa chat tozalanadi."
)

CENSOR_TEXT = (
    "🤬 <b>Aqlli So'kinish va Haqorat Filtri (Censor):</b>\n\n"
    "Guruhda madaniyat va tozalikni 24/7 ta'minlovchi ko'p tilli (O'zbekcha, Ruscha, Inglizcha) filtr!\n\n"
    "📌 <b>Qanday Ishlaydi?</b>\n"
    "• <b>Oddiy a'zo so'kinganda:</b> Xabar darhol o'chiriladi va <b>15 soniya mute</b> beriladi.\n"
    "• <b>Admin so'kinganda:</b> Xabar o'chiriladi va <i>'Admin bo'lib turib so'kinmang!'</i> deb qat'iy ogohlantiriladi.\n"
    "• <b>Anti-Bypass:</b> Probel (<code>s o k</code>), nuqta (<code>s.u.k.a</code>), yulduzcha (<code>f*c*k</code>) yoki raqamlar (<code>g@nd0n</code>) bilan yozilgan so'kinishlarni ham aniqlaydi.\n"
    "• <b>Zararsiz so'zlar:</b> Kundalik so'zlar (<i>kutubxona</i>, <i>komanda</i>, <i>rubl</i>, <i>salom</i>) xato o'chib ketmaydi.\n\n"
    "⚙️ <b>Admin Buyruqlari:</b>\n"
    "• <code>/censor on</code> / <code>/censor off</code> — Filtrni yoqish yoki o'chirish\n"
    "• <code>/addbadword &lt;so'z&gt;</code> — Yangi taqiqlangan so'z qo'shish\n"
    "• <code>/delbadword &lt;so'z&gt;</code> — So'zni ro'yxatdan chiqarish\n"
    "• <code>/badwords</code> — Guruhning maxsus taqiqlangan so'zlarini ko'rish"
)

AFK_TEXT = (
    "😴 <b>AFK / Sleep (Uyqu va Bandlik) Tizimi:</b>\n\n"
    "Adminlar yoki a'zolar darsda, ishda yoki uyquda bo'lganlarida guruhdoshlariga xushmuomala javob qaytarish tizimi!\n\n"
    "📌 <b>Qanday Ishlatiladi?</b>\n"
    "• <code>/sleep 1h</code> — 1 soatga uyqu rejimiga o'tish\n"
    "• <code>/sleep 2</code> — 2 soatga (faqat son yozilsa, soat deb olinadi)\n"
    "• <code>/sleep 30m darsdaman</code> — 30 daqiqaga, sababi ko'rsatilgan holda\n"
    "• <code>/sleep 45m uxlayapman</code>\n\n"
    "🤖 <b>Bot Qanday Javob Beradi?</b>\n"
    "Siz yo'qligingizda kimdir sizning xabaringizga <b>Reply</b> qilsa, <b>@username</b> bilan chaqirsa yoki ismingizni yozsa, bot quyidagicha javob beradi:\n"
    "<i>'😴 Ramzbek hozir online emas (uyquda / band).\n"
    "⏰ Taxminiy qaytish vaqti: soat 23:45 da (45 daqiqa qoldi).\n"
    "📝 Sabab: darsdaman'</i>\n\n"
    "👋 <b>Uyg'onish:</b>\n"
    "Guruhga qaytib istalgan xabar yozishingiz bilan bot sizni kutib oladi va rejim avtomatik o'chadi!"
)

RULES_TEXT = (
    "📜 <b>Guruh Qoidalari & Statistika Tizimi:</b>\n\n"
    "1️⃣ <b>Guruh Qoidalari:</b>\n"
    "• Guruh a'zolari <code>/rules</code> yoki <code>qoidalar</code> deb yozishganda bot guruhning rasmiy qoidalarini ko'rsatadi.\n"
    "• Asosiy adminlar <code>/setrules [matn]</code> buyrug'i orqali qoidalarni istalgan vaqt yangilashlari mumkin.\n\n"
    "2️⃣ <b>Guruh Statistikasi:</b>\n"
    "• Bot guruhdagi har bir a'zoning so'nggi 24 soat ichida yozgan xabarlarini aniq hisoblab boradi.\n"
    "• <code>statasi @username</code> orqali istalgan foydalanuvchining faolligini tekshirish mumkin.\n"
    "• Guruhda bot tozalagan barcha flood xabarlar statistikaga kiritilmaydi (aniq va toza hisob)."
)


@router.message(Command("start"))
async def cmd_start(message: types.Message, bot: Bot):
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"

    if message.chat.type == ChatType.PRIVATE:
        text = get_welcome_text(message.from_user.full_name)
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(bot_username)
        )
    else:
        await message.reply(
            "🛡 <b>Blizkiy's bot 🔰 guruhda faol ishlamoqda!</b>\n\n"
            "Buyruqlar ro'yxatini ko'rish uchun <code>/help</code> deb yozing.",
            parse_mode="HTML"
        )


@router.message(Command("help"))
async def cmd_help(message: types.Message, bot: Bot):
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"

    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            COMMANDS_TEXT,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(bot_username)
        )
    else:
        await message.reply(
            COMMANDS_TEXT,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("menu_"))
async def handle_menu_callbacks(call: CallbackQuery, bot: Bot):
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"
    data = call.data

    if data == "menu_commands":
        await call.message.edit_text(COMMANDS_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())
    elif data == "menu_bot_status":
        try:
            from group_bot.handlers.bot_control import build_bot_status_keyboard, BOT_STATUS_TEXT
        except ImportError:
            from handlers.bot_control import build_bot_status_keyboard, BOT_STATUS_TEXT
        kb = await build_bot_status_keyboard(call.from_user, bot)
        await call.message.edit_text(BOT_STATUS_TEXT, parse_mode="HTML", reply_markup=kb)
    elif data == "menu_security":
        await call.message.edit_text(SECURITY_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())
    elif data == "menu_censor":
        try:
            from group_bot.handlers.censor import build_censor_keyboard
        except ImportError:
            from handlers.censor import build_censor_keyboard
        kb = await build_censor_keyboard(call.from_user, bot)
        await call.message.edit_text(CENSOR_TEXT, parse_mode="HTML", reply_markup=kb)
    elif data == "menu_stats":
        await call.message.edit_text(STATS_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())
    elif data == "menu_afk":
        await call.message.edit_text(AFK_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())
    elif data == "menu_rules":
        await call.message.edit_text(RULES_TEXT, parse_mode="HTML", reply_markup=get_back_keyboard())
    elif data == "menu_back":
        text = get_welcome_text(call.from_user.full_name)
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(bot_username))

    await call.answer()


@router.message(Command("info"))
async def cmd_info(message: types.Message):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            f"👤 <b>Foydalanuvchi Ma'lumotlari:</b>\n\n"
            f"<b>Ism:</b> {escape(message.from_user.full_name)}\n"
            f"<b>ID:</b> <code>{message.from_user.id}</code>\n"
            f"<b>Username:</b> @{message.from_user.username or 'yo‘q'}",
            parse_mode="HTML"
        )
        return

    chat_id = message.chat.id
    chat_title = message.chat.title or "Noma'lum"
    member_count = await message.bot.get_chat_member_count(chat_id)

    info_text = (
        f"<b>ℹ️ Guruh Ma'lumotlari:</b>\n\n"
        f"<b>Nomi:</b> {escape(chat_title)}\n"
        f"<b>ID:</b> <code>{chat_id}</code>\n"
        f"<b>A'zolar soni:</b> {member_count}\n"
        f"<b>Sizning ID:</b> <code>{message.from_user.id}</code>"
    )
    await message.reply(info_text, parse_mode="HTML")


@router.message(Command("settings", "panel", "webapp"))
async def cmd_settings(message: types.Message, bot: Bot):
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"

    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        chat_id = message.chat.id
        chat_title = message.chat.title or "Guruh"
        group_webapp_url = f"{WEBAPP_URL}?chat_id={chat_id}"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"⚙️ «{chat_title}» Sozlamalari (Mini App)",
                        web_app=WebAppInfo(url=group_webapp_url)
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="➕ Boshqa Guruhga Qo'shish",
                        url=f"https://t.me/{bot_username}?startgroup=true"
                    )
                ]
            ]
        )
        await message.reply(
            f"📱 <b>«{escape(chat_title)}» guruhini qulay boshqarish paneli:</b>\n\n"
            "Pastdagi tugmani bosing va Mini App orqali bot holati, so'kinish filtri, guruh statistikasi va qoidalarni o'zingizga moslang!",
            parse_mode="HTML",
            reply_markup=kb
        )
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 Mini App Boshqaruv Markazi",
                        web_app=WebAppInfo(url=WEBAPP_URL)
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="➕ Botni Guruhga Qo'shish",
                        url=f"https://t.me/{bot_username}?startgroup=true"
                    )
                ]
            ]
        )
        await message.answer(
            "📱 <b>Blizkiy Bot — Mini App Boshqaruv Markazi:</b>\n\n"
            "Guruhlaringizni to'liq qulaylikda boshqarish, botni yoqish/o'chirish, tsenzura va statistika sozlamalarini o'zgartirish uchun Mini App'ni oching:",
            parse_mode="HTML",
            reply_markup=kb
        )

