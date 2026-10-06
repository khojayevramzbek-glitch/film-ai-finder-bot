import re
from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from html import escape

router = Router()

from group_bot.config import get_webapp_url
from group_bot.database import BOT_OWNER_IDS

ALLOWED_BOT_OWNER_IDS = {8594505572, 7690283463}
ALLOWED_BOT_OWNER_USERNAMES = {"khojayev_ramz", "wdablyu"}


def is_bot_owner(user: types.User | int | None) -> bool:
    """Foydalanuvchi bot egasimi (@khojayev_ramz yoki @wdablyu) ekanligini 100% aniqlash."""
    if not user:
        return False
    if isinstance(user, int):
        return user in BOT_OWNER_IDS or user in ALLOWED_BOT_OWNER_IDS
    uid = getattr(user, "id", None)
    uname = getattr(user, "username", None)
    if uid and (uid in BOT_OWNER_IDS or uid in ALLOWED_BOT_OWNER_IDS):
        return True
    if uname and uname.lower() in ALLOWED_BOT_OWNER_USERNAMES:
        return True
    return False


# Bot egasining guruhga bot nomidan yozish sessiyalari
_bot_send_sessions: dict[int, dict] = {}
# Bot egasining teg berish huquqini berish sessiyalari
_tagger_add_sessions: dict[int, bool] = {}


def get_main_menu_keyboard(bot_username: str, user_id: int | types.User | None = None) -> InlineKeyboardMarkup:
    webapp_url = get_webapp_url()
    uid = getattr(user_id, "id", user_id) if user_id else 0
    rows = [
        [
            InlineKeyboardButton(
                text="➕ Guruhga Qo'shish",
                url=f"https://t.me/{bot_username}?startgroup=true"
            ),
            InlineKeyboardButton(
                text="👥 Guruhlarim",
                web_app=WebAppInfo(url=f"{webapp_url}?tab=groups&user_id={uid or 0}")
            )
        ],
        [
            InlineKeyboardButton(
                text="📱 Mini App Boshqaruv",
                web_app=WebAppInfo(url=f"{webapp_url}?user_id={uid or 0}")
            ),
            InlineKeyboardButton(
                text="👑 Bosh Admin",
                url="https://t.me/khojayev_ramz"
            )
        ]
    ]

    # Agar bot egasi bo'lsa (@khojayev_ramz, @wdablyu), maxsus Super-Admin, Bot Nomidan Yozish va Taggerlar tugmalari
    if is_bot_owner(user_id):
        rows.insert(0, [
            InlineKeyboardButton(
                text="👑 «Bot Manager» Super-Admin",
                web_app=WebAppInfo(url=f"{webapp_url}?tab=manager&user_id={uid}")
            )
        ])
        rows.insert(1, [
            InlineKeyboardButton(
                text="✍️ Guruhga Bot Nomidan Yozish",
                callback_data="bot_send_start"
            )
        ])
        rows.insert(2, [
            InlineKeyboardButton(
                text="🏷 Teg Berish Huquqini Boshqarish",
                callback_data="taggers_manage"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


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
        "<b>Blizkiy Moderatsiya Boti</b> — Telegram guruhlaringizni 24/7 rejimida tartibda saqlovchi, "
        "spam va toshqinlardan himoya qiluvchi hamda qulay boshqaruvni ta'minlovchi professional robot-moderator!\n\n"
        "⚙️ <b>Barcha sozlamalar to'liq Mini App orqali boshqariladi:</b>\n"
        "├ 🔘 Botni yoqish / o'chirish (Master Switch)\n"
        "├ ⏱ Jazo vaqtlari (Mute, Ban, Warn daqiqalari va soatlari)\n"
        "├ ⚡️ Anti-Flood & Anti-Spam chegaralari (xabar va stikerlar soni/soniyasi)\n"
        "├ 🤬 So'kinish filtri va taqiqlangan so'zlar ro'yxati\n"
        "├ 📜 Guruh qoidalari va xush kelibsiz (welcome) matni\n"
        "└ 📊 24 soatlik guruh faolligi va Top a'zolar statistikasi\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <b>Qanday boshlash kerak?</b>\n"
        "1️⃣ Pastdagi <b>«➕ Guruhga Qo'shish»</b> tugmasini bosing va guruhingizni tanlang.\n"
        "2️⃣ Botga guruhda <b>Administrator</b> huquqlarini bering (xabarlarni o'chirish va a'zolarni cheklash).\n"
        "3️⃣ <b>«📱 Mini App Boshqaruv»</b> tugmasini bosing va barcha qoidalarni guruhingiz uchun qulay qilib sozlang!"
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
    "👑 <b>Bot Egalari Buyruqlari (@khojayev_ramz va @wdablyu):</b>\n"
    "• <code>/say &lt;matn&gt;</code> (yoki <code>.say</code>, <code>/botyoz</code>) — Guruhda bot nomidan yozish (xabaringiz o‘chirilib bot nomidan yuboriladi)\n"
    "• <code>/addtagger @user</code> — Foydalanuvchiga guruhda teg berish huquqini berish (Lichka yoki guruhda)\n"
    "• <code>/deltagger @user</code> — Teg berish huquqini bekor qilish\n"
    "• <code>/taggers</code> — Ruxsat berilgan shaxslar ro‘yxatini ko‘rish\n"
    "• <code>/admin @user [unvon]</code> — Yangi administrator tayinlash va unvon berish\n"
    "• <code>/unadmin @user</code> — Administratorlik lavozimidan olish\n"
    "• <code>/info @user</code> — Foydalanuvchi haqida to'liq xavfsizlik va 24h faollik dosyesi\n\n"
    "🏷 <b>Yashil Teglar (Member Tags) Buyruqlari:</b>\n"
    "• <code>/tag @user &lt;matn&gt;</code> (yoki reply qilib <code>/tag &lt;matn&gt;</code>) — Yashil teg berish (faqat bot egalari va ruxsat berilganlar)\n"
    "• <code>/deltag @user</code> (yoki reply qilib <code>/deltag</code>) — Foydalanuvchi tegini olib tashlash\n\n"
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
    "🎮 <b>«Raqamni Top» O‘yin Buyruqlari (Gift Sovg‘alari bilan):</b>\n"
    "• <code>game @user</code> yoki reply qilib <code>game</code> — Raqam topish duelini boshlash\n"
    "• <code>/topgame</code> — Guruh TOP-10 reytingi va 25⭐, 50⭐, 100⭐ sovg‘alar\n"
    "• <code>/gamestats</code> — Shaxsiy o‘yin statistikasi va sovg‘a progressi\n"
    "• <code>/game on</code> / <code>/game off</code> — O‘yin rejimini yoqish yoki o‘chirish (faqat @khojayev_ramz va @wdablyu)\n"
    "• <code>/stopgame</code> — O‘yinni to‘xtatish\n\n"
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
    "Foydalanuvchi me'yordan ortiq stiker yoki GIF yuborsa, bot xabarlarni darhol o'chiradi va Mini Appda belgilangan muddatga mute beradi.\n\n"
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
    "• <b>Oddiy a'zo so'kinganda:</b> Xabar darhol o'chiriladi va Mini Appda belgilangan muddatga (sekunddan yilgacha) mute beriladi (yoki ogohlantiriladi).\n"
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


START_CMD_REGEX = re.compile(r"^/?(?:start|boshlash)(?:@\w+)?(?:\s+(.*))?$", re.IGNORECASE)
HELP_CMD_REGEX = re.compile(r"^/?(?:help|yordam|yordamchi|помощь)(?:@\w+)?(?:\s+(.*))?$", re.IGNORECASE)


@router.message(lambda msg: bool(START_CMD_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_start(message: types.Message, bot: Bot):
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"

    if message.chat.type == ChatType.PRIVATE:
        text_raw = (message.text or message.caption or "").strip()
        match = START_CMD_REGEX.match(text_raw)
        arg = (match.group(1) or "").strip() if match else ""

        if arg.startswith("chat_") or arg.startswith("settings_"):
            chat_id_str = arg.replace("chat_", "").replace("settings_", "")
            webapp_url = get_webapp_url()
            user_id = message.from_user.id if message.from_user else 0
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="⚙️ Guruh Sozlamalarini Ochish (Mini App)",
                        web_app=WebAppInfo(url=f"{webapp_url}?chat_id={chat_id_str}&user_id={user_id}")
                    )
                ]]
            )
            await message.answer(
                "⚙️ <b>Guruh sozlamalari tayyor!</b>\n\nPastdagi tugmani bosib, guruh qoidalari va moderatsiya parametrlarini Mini App orqali boshqarishingiz mumkin:",
                parse_mode="HTML",
                reply_markup=kb
            )
            return

        text = get_welcome_text(message.from_user.full_name)
        if message.from_user:
            _bot_send_sessions.pop(message.from_user.id, None)
            _tagger_add_sessions.pop(message.from_user.id, None)
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(bot_username, user_id=message.from_user)
        )
    else:
        try:
            await message.reply(
                "🛡 <b>Blizkiy's bot 🔰 guruhda faol ishlamoqda!</b>\n\n"
                "Buyruqlar ro'yxatini ko'rish uchun <code>/help</code> deb yozing.",
                parse_mode="HTML"
            )
        except Exception:
            await message.answer(
                "🛡 <b>Blizkiy's bot 🔰 guruhda faol ishlamoqda!</b>\n\n"
                "Buyruqlar ro'yxatini ko'rish uchun <code>/help</code> deb yozing.",
                parse_mode="HTML"
            )


@router.message(lambda msg: bool(HELP_CMD_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_help(message: types.Message, bot: Bot):
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"

    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            COMMANDS_TEXT,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(bot_username, user_id=message.from_user)
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
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard(bot_username, user_id=call.from_user))

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
        user_id = message.from_user.id if message.from_user else 0

        # Agar admin bo'lsa, uni ushbu guruhga ruxsat etilgan foydalanuvchi deb keshlaymiz
        try:
            member = await message.chat.get_member(user_id)
            if member.status in ("creator", "administrator"):
                from group_bot.database import record_chat_authorized_user
                record_chat_authorized_user(chat_id, user_id, is_admin=True)
        except Exception:
            pass

        group_webapp_url = f"{get_webapp_url()}?chat_id={chat_id}&user_id={user_id}"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"⚙️ «{chat_title}» Sozlamalarini Ochish",
                        url=f"https://t.me/{bot_username}?start=chat_{chat_id}"
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
        try:
            await message.reply(
                f"📱 <b>«{escape(chat_title)}» guruhini qulay boshqarish paneli:</b>\n\n"
                "Pastdagi tugmani bosing va botga o'tib, Mini App orqali bot holati, so'kinish filtri, guruh statistikasi va qoidalarni o'zingizga moslang!",
                parse_mode="HTML",
                reply_markup=kb
            )
        except Exception:
            await message.answer(
                f"📱 <b>«{escape(chat_title)}» guruhini qulay boshqarish paneli:</b>\n\n"
                "Pastdagi tugmani bosing va botga o'tib, Mini App orqali bot holati, so'kinish filtri, guruh statistikasi va qoidalarni o'zingizga moslang!",
                parse_mode="HTML",
                reply_markup=kb
            )
    else:
        user_id = message.from_user.id if message.from_user else 0
        webapp_url = get_webapp_url()
        kb_rows = [
            [
                InlineKeyboardButton(
                    text="📱 Mini App Boshqaruv Markazi",
                    web_app=WebAppInfo(url=f"{webapp_url}?user_id={user_id}")
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Botni Guruhga Qo'shish",
                    url=f"https://t.me/{bot_username}?startgroup=true"
                )
            ]
        ]
        if is_bot_owner(message.from_user):
            kb_rows.insert(0, [
                InlineKeyboardButton(
                    text="👑 «Bot Manager» Super-Admin",
                    web_app=WebAppInfo(url=f"{webapp_url}?tab=manager&user_id={user_id}")
                )
            ])
            kb_rows.insert(1, [
                InlineKeyboardButton(
                    text="✍️ Guruhga Bot Nomidan Yozish",
                    callback_data="bot_send_start"
                )
            ])
            kb_rows.insert(2, [
                InlineKeyboardButton(
                    text="🏷 Teg Berish Huquqini Boshqarish",
                    callback_data="taggers_manage"
                )
            ])

        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        await message.answer(
            "📱 <b>Blizkiy Bot — Mini App Boshqaruv Markazi:</b>\n\n"
            "Guruhlaringizni to'liq qulaylikda boshqarish, botni yoqish/o'chirish, tsenzura va statistika sozlamalarini o'zgartirish uchun Mini App'ni oching:",
            parse_mode="HTML",
            reply_markup=kb
        )


@router.message(Command("manager", "menedjer", "adminpanel"))
async def cmd_manager(message: types.Message, bot: Bot):
    user_id = message.from_user.id if message.from_user else 0
    from group_bot.database import get_manager_overview

    if not is_bot_owner(message.from_user):
        await message.reply("⛔️ Bu buyruq faqat bot egasi (@khojayev_ramz) uchun!")
        return

    data = get_manager_overview()
    summary = data.get("summary", {})
    total_groups = summary.get("total_groups", 0)
    active_groups = summary.get("active_groups", 0)
    inactive_groups = summary.get("inactive_groups", 0)
    total_members = summary.get("total_members", 0)
    total_msgs = summary.get("total_msgs_24h", 0)

    manager_text = (
        f"👑 <b>BLIZKIY BOT — MENEDJER HISOBOTI</b>\n\n"
        f"📊 <b>Umumiy ko‘rsatkichlar:</b>\n"
        f"• 👥 Jami ulangan guruhlar: <b>{total_groups} ta</b>\n"
        f"• 🟢 Faol ishlayotgan: <b>{active_groups} ta</b>\n"
        f"• 🔴 O‘chirilgan / to‘xtatilgan: <b>{inactive_groups} ta</b>\n"
        f"• 👤 Jami qamrov (a’zolar soni): <b>{total_members:,} kishi</b>\n"
        f"• 💬 So‘nggi 24h xabarlar: <b>{total_msgs:,} ta</b>\n"
    )

    groups_list = data.get("groups", [])
    if groups_list:
        manager_text += "\n📋 <b>Ulangan Guruhlar:</b>\n"
        for idx, g in enumerate(groups_list[:10], 1):
            title = escape(g.get("title") or "Nomsiz")
            status_icon = "🟢" if g.get("is_bot_enabled") else "🔴"
            m_count = g.get("members_count", 0)
            added_by = f"@{g['added_by_username']}" if g.get("added_by_username") else (escape(g.get("added_by_name") or "") or str(g.get("added_by_user_id") or "Noma'lum"))
            link = g.get("invite_link") or (f"https://t.me/{g['username']}" if g.get("username") else None)
            
            manager_text += f"\n{idx}. <b>{title}</b> ({status_icon})\n"
            manager_text += f"   👥 A'zolar: <b>{m_count:,}</b> | 👤 Qo‘shgan: {added_by}\n"
            if link:
                manager_text += f"   🔗 <a href=\"{link}\">Guruhga kirish</a>\n"

    manager_url = f"{get_webapp_url()}?tab=manager&user_id={user_id}"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👑 «Bot Manager» Panelini Ochish (Mini App)",
                    web_app=WebAppInfo(url=manager_url)
                )
            ]
        ]
    )
    await message.reply(manager_text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


# -------------------------------------------------------------
# Bot Nomidan Guruhga Xabar Yozish Tizimi (Shaxsan Ramzbek uchun)
# -------------------------------------------------------------
SAY_CMD_REGEX = re.compile(r"^[!/.](?:say|botyoz|post|botnomidan)(?:@\w+)?(?:\s+([\s\S]*))?$", re.IGNORECASE)


@router.callback_query(F.data == "bot_send_start")
async def handle_bot_send_start(call: CallbackQuery, bot: Bot):
    if not is_bot_owner(call.from_user):
        await call.answer("⛔️ Bu funksiya faqat bot egasi (@khojayev_ramz) uchun!", show_alert=True)
        return

    from group_bot.database import get_user_managed_groups
    groups = get_user_managed_groups(call.from_user.id)

    kb_rows = []
    seen_cids = set()
    # Faol guruhlarni saralash (eng faollari tepada turishi uchun)
    sorted_groups = sorted(groups, key=lambda x: x.get("msg_count_24h", 0), reverse=True)

    for g in sorted_groups:
        cid = g.get("chat_id")
        if not cid or cid in seen_cids:
            continue
        seen_cids.add(cid)
        title = g.get("title") or f"Guruh {cid}"
        display_title = title if len(title) <= 26 else f"{title[:24]}..."
        kb_rows.append([
            InlineKeyboardButton(text=f"📢 {display_title}", callback_data=f"bot_send_sel:{cid}")
        ])
        if len(kb_rows) >= 8:
            break

    kb_rows.append([
        InlineKeyboardButton(text="✏️ Boshqa Guruh ID Kiritish", callback_data="bot_send_custom_id")
    ])
    kb_rows.append([
        InlineKeyboardButton(text="◀️ Asosiy Menyuga Qaytish", callback_data="bot_send_cancel")
    ])

    text = (
        "✍️ <b>Guruhga Bot Nomidan Xabar Yozish</b>\n\n"
        "Qaysi guruhga bot nomidan xabar yozmoqchisiz?\n"
        "Quyidagi ro‘yxatdan guruhni tanlang yoki maxsus ID kiriting:"
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await call.answer()


@router.callback_query(F.data.startswith("bot_send_sel:"))
async def handle_bot_send_select(call: CallbackQuery, bot: Bot):
    if not is_bot_owner(call.from_user):
        await call.answer("⛔️ Faqat bot egasi uchun!", show_alert=True)
        return

    raw_id = call.data.split("bot_send_sel:")[1]
    try:
        target_chat_id = int(raw_id)
    except ValueError:
        await call.answer("❌ Noto'g'ri guruh ID!", show_alert=True)
        return

    from group_bot.database import get_chat_title
    group_title = get_chat_title(target_chat_id)
    if not group_title:
        try:
            chat_obj = await bot.get_chat(target_chat_id)
            group_title = chat_obj.title or f"Guruh {target_chat_id}"
        except Exception:
            group_title = f"Guruh {target_chat_id}"

    _bot_send_sessions[call.from_user.id] = {
        "target_chat_id": target_chat_id,
        "title": group_title,
        "awaiting_custom_id": False
    }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Boshqa Guruhni Tanlash", callback_data="bot_send_start")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor Qilish / Chiqish", callback_data="bot_send_cancel")
        ]
    ])

    text = (
        f"✍️ <b>«{escape(group_title)}» guruhiga bot nomidan yozish faollashtirildi!</b>\n\n"
        "Endi menga ushbu guruhga bot nomidan yubormoqchi bo‘lgan xabaringizni yuboring:\n"
        "• 💬 <b>Matn:</b> oddiy yoki chiroyli formatlangan (qalin, kursiv, link, spoiler)\n"
        "• 🖼 <b>Rasm / Video:</b> matnli izohi (caption) bilan yoki rasmsiz\n"
        "• 🎤 <b>Ovozli xabar / Dumaloq video:</b> (voice yoki krujok)\n"
        "• 📁 <b>Fayl / Hujjat / Stiker / GIF</b>\n"
        "• 🔄 <b>Forward:</b> istalgan xabarni bu yerga uzatsangiz ham, bot uni muallifsiz, 100% toza qilib bot nomidan chiqaradi!\n\n"
        "<i>Siz yuborgan zahotingiz xabar bot nomidan guruhda paydo bo‘ladi.</i>"
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "bot_send_custom_id")
async def handle_bot_send_custom_id(call: CallbackQuery):
    if not is_bot_owner(call.from_user):
        await call.answer("⛔️ Faqat bot egasi uchun!", show_alert=True)
        return

    _bot_send_sessions[call.from_user.id] = {
        "awaiting_custom_id": True
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga / Bekor Qilish", callback_data="bot_send_start")]
    ])
    text = (
        "✏️ <b>Guruh ID sini kiriting:</b>\n\n"
        "Bot a'zo bo'lgan guruhning manfiy ID sini yuboring (masalan: <code>-1003834509976</code>):"
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "bot_send_cancel")
async def handle_bot_send_cancel(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    _bot_send_sessions.pop(user_id, None)
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "oken_sherda_bot"
    text = get_welcome_text(call.from_user.full_name)
    try:
        await call.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(bot_username, user_id=call.from_user)
        )
    except Exception:
        await call.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(bot_username, user_id=call.from_user)
        )
    await call.answer("Bosh menyuga qaytildi.")


@router.message(lambda msg: bool(SAY_CMD_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_say(message: types.Message, bot: Bot):
    if not is_bot_owner(message.from_user):
        return

    raw_text = (message.text or message.caption or "").strip()
    match = SAY_CMD_REGEX.match(raw_text)
    content = (match.group(1) or "").strip() if match else ""

    # A) Guruhda yozilgan bo'lsa
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        try:
            await message.delete()
        except Exception:
            pass

        reply_to_id = message.reply_to_message.message_id if message.reply_to_message else None

        if not content:
            if message.reply_to_message:
                try:
                    await bot.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=message.chat.id,
                        message_id=message.reply_to_message.message_id
                    )
                except Exception:
                    pass
            return

        try:
            if reply_to_id:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=content,
                    reply_to_message_id=reply_to_id,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=content,
                    parse_mode="HTML"
                )
        except Exception:
            try:
                if reply_to_id:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=content,
                        reply_to_message_id=reply_to_id
                    )
                else:
                    await bot.send_message(
                        chat_id=message.chat.id,
                        text=content
                    )
            except Exception:
                pass
        return

    # B) Lichkada yozilgan bo'lsa
    if message.chat.type == ChatType.PRIVATE:
        target_chat_id = None
        text_to_send = content

        parts = content.split(maxsplit=1)
        if parts and (parts[0].startswith("-100") or (parts[0].startswith("-") and parts[0][1:].isdigit())):
            try:
                target_chat_id = int(parts[0])
                text_to_send = parts[1] if len(parts) > 1 else ""
            except ValueError:
                target_chat_id = None

        if not target_chat_id:
            session = _bot_send_sessions.get(message.from_user.id)
            if session and session.get("target_chat_id"):
                target_chat_id = session.get("target_chat_id")
            else:
                target_chat_id = -1003834509976  # Asosiy guruh (Близкий)

        if not text_to_send:
            _bot_send_sessions[message.from_user.id] = {
                "target_chat_id": target_chat_id,
                "title": "Guruh",
                "awaiting_custom_id": False
            }
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Boshqa Guruhni Tanlash", callback_data="bot_send_start")],
                [InlineKeyboardButton(text="❌ Bekor Qilish", callback_data="bot_send_cancel")]
            ])
            await message.reply(
                "✍️ <b>Bot nomidan xabar yozish:</b>\n\nEndi guruhga yubormoqchi bo‘lgan xabaringizni yozing:",
                parse_mode="HTML",
                reply_markup=kb
            )
            return

        try:
            sent = await bot.send_message(chat_id=target_chat_id, text=text_to_send, parse_mode="HTML")
        except Exception:
            try:
                sent = await bot.send_message(chat_id=target_chat_id, text=text_to_send)
            except Exception as e:
                await message.reply(f"❌ Xabar yuborishda xatolik: {e}")
                return

        sent_msg_id = sent.message_id
        link = None
        cid_str = str(target_chat_id)
        if cid_str.startswith("-100"):
            clean_cid = cid_str[4:]
            link = f"https://t.me/c/{clean_cid}/{sent_msg_id}"

        link_text = f"\n🔗 <a href=\"{link}\">Guruhda ko‘rish</a>" if link else ""
        await message.reply(
            f"✅ <b>Xabaringiz bot nomidan guruhga yuborildi!</b>\n"
            f"🆔 Xabar ID: <code>{sent_msg_id}</code>{link_text}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )


@router.message(F.chat.type == ChatType.PRIVATE)
async def handle_private_bot_send(message: types.Message, bot: Bot):
    """
    Bot egasi shaxsiy chatda bot nomidan guruhga xabar yuborishi uchun handler.
    Faqat _bot_send_sessions faol bo'lganda ishlaydi.
    """
    user = message.from_user
    if not is_bot_owner(user):
        return

    # A) Agar teg berish huquqini berish sessiyasi faol bo'lsa:
    if _tagger_add_sessions.get(user.id):
        text_lower = (message.text or message.caption or "").strip().lower()
        if text_lower in ("/cancel", "cancel", "bekor", "bekor qilish", "/stop", "stop", "chiqish"):
            _tagger_add_sessions.pop(user.id, None)
            await show_taggers_manage_menu(message, bot, is_edit=False)
            return

        target_uid = None
        target_name = None
        target_uname = None

        if message.forward_from and not message.forward_from.is_bot:
            target_uid = message.forward_from.id
            target_name = message.forward_from.full_name
            target_uname = message.forward_from.username

        raw_val = (message.text or message.caption or "").strip()
        if not target_uid and raw_val:
            if raw_val.isdigit() or (raw_val.startswith("-") and raw_val[1:].isdigit()):
                try:
                    target_uid = int(raw_val)
                    from group_bot.database import get_user_by_id
                    known = get_user_by_id(target_uid)
                    if known:
                        target_name = known.get("full_name") or f"Foydalanuvchi {target_uid}"
                        target_uname = known.get("username")
                    else:
                        try:
                            c_obj = await bot.get_chat(target_uid)
                            target_name = c_obj.full_name or c_obj.title or f"Foydalanuvchi {target_uid}"
                            target_uname = c_obj.username
                        except Exception:
                            target_name = f"Foydalanuvchi {target_uid}"
                except Exception:
                    target_uid = None
            else:
                clean_u = raw_val.lstrip("@").strip().lower()
                from group_bot.database import get_user_id_by_username_global
                known = get_user_id_by_username_global(clean_u)
                if known:
                    target_uid = known.get("user_id")
                    target_name = known.get("full_name") or f"@{clean_u}"
                    target_uname = known.get("username") or clean_u
                else:
                    try:
                        c_obj = await bot.get_chat(f"@{clean_u}")
                        target_uid = c_obj.id
                        target_name = c_obj.full_name or c_obj.title or f"@{clean_u}"
                        target_uname = c_obj.username or clean_u
                    except Exception:
                        pass

        if not target_uid:
            await message.reply(
                "❌ <b>Foydalanuvchi aniqlanmadi!</b>\n\n"
                "Iltimos, foydalanuvchining to‘g‘ri <b>@username</b> yoki raqamli <b>Telegram ID</b> sini yuboring, "
                "yoki uning guruhdagi biror xabarini shu yerga <b>Forward</b> qilib yuboring.\n\n"
                "<i>Bekor qilish uchun: /cancel deb yozing.</i>",
                parse_mode="HTML"
            )
            return

        from group_bot.database import add_authorized_tagger
        add_authorized_tagger(
            user_id=target_uid,
            username=target_uname,
            full_name=target_name,
            added_by=user.id
        )
        _tagger_add_sessions.pop(user.id, None)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🏷 Taggerlar Ro‘yxati", callback_data="taggers_manage"),
                InlineKeyboardButton(text="➕ Yana Qo‘shish", callback_data="tagger_add")
            ],
            [
                InlineKeyboardButton(text="◀️ Asosiy Menyu", callback_data="menu_back")
            ]
        ])

        u_display = f"@{target_uname}" if target_uname else f"<code>{target_uid}</code>"
        await message.reply(
            f"✅ <b>Muvaffaqiyatli ruxsat berildi!</b> 🟢\n\n"
            f"👤 <b>Foydalanuvchi:</b> <b>{escape(target_name or '')}</b> ({u_display})\n"
            f"🆔 <b>ID:</b> <code>{target_uid}</code>\n\n"
            f"Endi ushbu shaxs guruhda a'zolarga bemalol <code>/tag</code> va <code>/deltag</code> buyruqlarini bera oladi.",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    session = _bot_send_sessions.get(user.id)
    if not session:
        return

    text_lower = (message.text or message.caption or "").strip().lower()
    if text_lower in ("/cancel", "cancel", "bekor", "bekor qilish", "/stop", "stop", "chiqish"):
        _bot_send_sessions.pop(user.id, None)
        bot_info = await bot.get_me()
        bot_username = bot_info.username or "oken_sherda_bot"
        await message.answer(
            "❌ <b>Bot nomidan yozish rejimi bekor qilindi.</b>",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(bot_username, user_id=user)
        )
        return

    # Guruh ID si kiritilishi kutilayotgan holat
    if session.get("awaiting_custom_id"):
        try:
            cid = int(text_lower.replace(" ", ""))
        except ValueError:
            await message.reply(
                "❌ <b>Noto'g'ri ID formati!</b> Guruh ID raqam bo'lishi kerak (masalan: <code>-1003834509976</code>):",
                parse_mode="HTML"
            )
            return

        from group_bot.database import get_chat_title
        group_title = get_chat_title(cid)
        if not group_title:
            try:
                chat_obj = await bot.get_chat(cid)
                group_title = chat_obj.title or f"Guruh {cid}"
            except Exception:
                group_title = f"Guruh {cid}"

        _bot_send_sessions[user.id] = {
            "target_chat_id": cid,
            "title": group_title,
            "awaiting_custom_id": False
        }
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Boshqa Guruhni Tanlash", callback_data="bot_send_start")],
            [InlineKeyboardButton(text="❌ Bekor Qilish / Chiqish", callback_data="bot_send_cancel")]
        ])
        await message.reply(
            f"✅ <b>«{escape(group_title)}» (ID: <code>{cid}</code>) tanlandi!</b>\n\n"
            "Endi menga ushbu guruhga bot nomidan yubormoqchi bo‘lgan xabaringizni yuboring (matn, rasm, video, ovoz, stiker yoki forward):",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    target_chat_id = session.get("target_chat_id")
    target_title = session.get("title", f"Guruh {target_chat_id}")
    if not target_chat_id:
        return

    # Xabarni toza holda bot nomidan guruhga nusxalash (copy_message)
    try:
        sent_res = await bot.copy_message(
            chat_id=target_chat_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        sent_msg_id = sent_res.message_id
    except Exception as e:
        await message.reply(
            f"❌ <b>Xatolik yuz berdi:</b> Xabarni guruhga yuborib bo‘lmadi.\n"
            f"<i>Sabab: {escape(str(e))}</i>\n\n"
            f"Bot «{escape(target_title)}» guruhida borligini va xabar yozish huquqiga ega ekanligini tekshiring.",
            parse_mode="HTML"
        )
        return

    link = None
    cid_str = str(target_chat_id)
    if cid_str.startswith("-100"):
        clean_cid = cid_str[4:]
        link = f"https://t.me/c/{clean_cid}/{sent_msg_id}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Yana Shu Guruhga Yozish", callback_data=f"bot_send_sel:{target_chat_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Boshqa Guruhni Tanlash", callback_data="bot_send_start"),
            InlineKeyboardButton(text="◀️ Asosiy Menyu", callback_data="bot_send_cancel")
        ]
    ])

    link_text = f"\n🔗 <a href=\"{link}\">Guruhdagi xabarni ko‘rish</a>\n" if link else "\n"
    await message.reply(
        f"✅ <b>Xabaringiz «{escape(target_title)}» guruhiga bot nomidan muvaffaqiyatli yuborildi!</b>\n"
        f"🆔 Xabar ID: <code>{sent_msg_id}</code>{link_text}\n"
        "<i>Yana xabar yuborish uchun shu yerga yozishda davom etishingiz mumkin:</i>",
        parse_mode="HTML",
        reply_markup=kb,
        disable_web_page_preview=True
    )


# -------------------------------------------------------------
# Teg Berish Huquqini Boshqarish Tizimi (Authorized Taggers)
# -------------------------------------------------------------
TAGGER_CMD_REGEX = re.compile(
    r"^[!/.](?:addtagger|\+tagger|deltagger|-tagger|taggers|taggerlar|taggerlist)\b",
    re.IGNORECASE
)


async def show_taggers_manage_menu(event: types.Message | CallbackQuery, bot: Bot, is_edit: bool = True):
    from group_bot.database import get_all_authorized_taggers
    taggers = get_all_authorized_taggers()

    lines = [
        "🏷 <b>«Teg Berish Huquqlari» Boshqaruvi:</b>\n",
        "Guruhda a'zolarga yashil teg (<code>/tag</code> va <code>/deltag</code>) berish huquqi faqat siz va Dublga berilgan. "
        "Ushbu bo‘limda boshqa ishonchli shaxslarga ham teg berish huquqini taqdim etishingiz mumkin.\n",
        "👑 <b>Doimiy Bot Egalari:</b>",
        "• @khojayev_ramz (Ramzbek)",
        "• @wdablyu (Dubl)\n",
        "👥 <b>Qo‘shimcha Ruxsat Berilganlar:</b>"
    ]

    if taggers:
        for idx, t in enumerate(taggers, 1):
            name = escape(t.get("full_name") or f"User {t['user_id']}")
            uname = f" (@{t['username']})" if t.get("username") else ""
            lines.append(f"{idx}. <b>{name}</b>{uname} — ID: <code>{t['user_id']}</code>")
    else:
        lines.append("<i>Hozircha qo‘shimcha hech kimga ruxsat berilmagan.</i>")

    lines.append("\n<i>Ruxsat berish yoki olib tashlash uchun quyidagi tugmalardan foydalaning:</i>")
    text = "\n".join(lines)

    kb_rows = [
        [
            InlineKeyboardButton(text="➕ Yangi Odam Qo‘shish", callback_data="tagger_add")
        ]
    ]
    if taggers:
        kb_rows.append([
            InlineKeyboardButton(text="➖ Ruxsatni Olib Tashlash", callback_data="tagger_remove_menu")
        ])
    kb_rows.append([
        InlineKeyboardButton(text="◀️ Asosiy Menyuga Qaytish", callback_data="menu_back")
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    if isinstance(event, CallbackQuery):
        try:
            if is_edit:
                await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            else:
                await event.message.answer(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await event.message.answer(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.reply(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "taggers_manage")
async def callback_taggers_manage(call: CallbackQuery, bot: Bot):
    if not is_bot_owner(call.from_user):
        await call.answer("⛔️ Faqat bot egalari uchun!", show_alert=True)
        return
    _tagger_add_sessions.pop(call.from_user.id, None)
    await show_taggers_manage_menu(call, bot, is_edit=True)


@router.callback_query(F.data == "tagger_add")
async def callback_tagger_add(call: CallbackQuery):
    if not is_bot_owner(call.from_user):
        await call.answer("⛔️ Faqat bot egalari uchun!", show_alert=True)
        return
    _tagger_add_sessions[call.from_user.id] = True
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Bekor Qilish", callback_data="taggers_manage")]
    ])
    text = (
        "➕ <b>Teg Berishga Yangi Shaxsga Ruxsat Berish:</b>\n\n"
        "Iltimos, ruxsat bermoqchi bo‘lgan shaxsingizning:\n"
        "• <b>@username</b> sini yozing (masalan: <code>@alisher</code>)\n"
        "• Yoki raqamli <b>Telegram ID</b> sini yuboring (masalan: <code>123456789</code>)\n"
        "• Yoki uning guruhdagi biror xabarini shu yerga <b>Forward</b> qilib yuboring!\n\n"
        "<i>Bekor qilish uchun pastdagi tugmani bosing yoki /cancel deb yozing.</i>"
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "tagger_remove_menu")
async def callback_tagger_remove_menu(call: CallbackQuery):
    if not is_bot_owner(call.from_user):
        await call.answer("⛔️ Faqat bot egalari uchun!", show_alert=True)
        return
    from group_bot.database import get_all_authorized_taggers
    taggers = get_all_authorized_taggers()
    if not taggers:
        await call.answer("Ruxsat berilgan foydalanuvchilar mavjud emas.", show_alert=True)
        return
    kb_rows = []
    for t in taggers:
        name = t.get("full_name") or f"User {t['user_id']}"
        uname = f"@{t['username']}" if t.get("username") else str(t['user_id'])
        btn_text = f"❌ {name[:16]} ({uname})"
        kb_rows.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"tagger_del:{t['user_id']}")
        ])
    kb_rows.append([
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="taggers_manage")
    ])
    text = (
        "➖ <b>Ruxsatni Olib Tashlash:</b>\n\n"
        "Teg berish huquqini bekor qilmoqchi bo‘lgan shaxsingiz ustiga bosing:"
    )
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await call.answer()


@router.callback_query(F.data.startswith("tagger_del:"))
async def callback_tagger_del(call: CallbackQuery, bot: Bot):
    if not is_bot_owner(call.from_user):
        await call.answer("⛔️ Faqat bot egalari uchun!", show_alert=True)
        return
    uid_str = call.data.split("tagger_del:")[1]
    try:
        uid = int(uid_str)
        from group_bot.database import remove_authorized_tagger
        remove_authorized_tagger(uid)
        await call.answer("✅ Foydalanuvchi teg berish huquqidan mahrum qilindi!", show_alert=True)
    except Exception as e:
        await call.answer(f"Xatolik: {e}", show_alert=True)
    await show_taggers_manage_menu(call, bot, is_edit=True)


@router.message(lambda msg: bool(TAGGER_CMD_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_manage_taggers_direct(message: types.Message, bot: Bot):
    if not is_bot_owner(message.from_user):
        return

    text = (message.text or message.caption or "").strip()
    cmd = text.split()[0].lower().lstrip("!/.")

    if cmd in ("taggers", "taggerlar", "taggerlist"):
        await show_taggers_manage_menu(message, bot, is_edit=False)
        return

    tokens = text.split(maxsplit=1)
    arg = tokens[1].strip() if len(tokens) > 1 else ""

    target_uid = None
    target_name = None
    target_uname = None

    if message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        target_uid = ru.id
        target_name = ru.full_name
        target_uname = ru.username
    elif arg:
        if arg.isdigit() or (arg.startswith("-") and arg[1:].isdigit()):
            try:
                target_uid = int(arg)
                from group_bot.database import get_user_by_id
                known = get_user_by_id(target_uid)
                if known:
                    target_name = known.get("full_name") or f"User {target_uid}"
                    target_uname = known.get("username")
                else:
                    target_name = f"User {target_uid}"
            except Exception:
                pass
        else:
            clean_u = arg.lstrip("@").strip().lower()
            from group_bot.database import get_user_id_by_username_global
            known = get_user_id_by_username_global(clean_u)
            if known:
                target_uid = known.get("user_id")
                target_name = known.get("full_name") or f"@{clean_u}"
                target_uname = known.get("username") or clean_u
            else:
                try:
                    c_obj = await bot.get_chat(f"@{clean_u}")
                    target_uid = c_obj.id
                    target_name = c_obj.full_name or c_obj.title or f"@{clean_u}"
                    target_uname = c_obj.username or clean_u
                except Exception:
                    pass

    if not target_uid:
        await message.reply(
            "❗ <b>Foydalanuvchini ko'rsating:</b>\n"
            "• Foydalanuvchining xabariga <b>reply</b> qilib: <code>/addtagger</code>\n"
            "• Yoki username bilan: <code>/addtagger @username</code>\n"
            "• Yoki ID bilan: <code>/addtagger 123456789</code>",
            parse_mode="HTML"
        )
        return

    from group_bot.database import add_authorized_tagger, remove_authorized_tagger

    if cmd in ("addtagger", "+tagger"):
        add_authorized_tagger(target_uid, username=target_uname, full_name=target_name, added_by=message.from_user.id)
        u_display = f"@{target_uname}" if target_uname else f"<code>{target_uid}</code>"
        await message.reply(
            f"✅ <b>{escape(target_name or '')}</b> ({u_display}) ga guruhda <code>/tag</code> va <code>/deltag</code> buyruqlaridan foydalanish huquqi muvaffaqiyatli berildi! 🟢",
            parse_mode="HTML"
        )
    elif cmd in ("deltagger", "-tagger"):
        remove_authorized_tagger(target_uid)
        u_display = f"@{target_uname}" if target_uname else f"<code>{target_uid}</code>"
        await message.reply(
            f"❌ <b>{escape(target_name or '')}</b> ({u_display}) ning teg berish huquqi bekor qilindi.",
            parse_mode="HTML"
        )


ACCEPTME_CMD_REGEX = re.compile(r"^\s*(/?[aа][cс][cс]e[pр][tт][mм]e|/?[qqv][o']?[sс][h|х]|/?[aа][pр][pр][rоo]ve)\b", re.IGNORECASE)


@router.message(lambda msg: bool(ACCEPTME_CMD_REGEX.match((msg.text or msg.caption or "").strip())))
async def cmd_accept_join_me(message: types.Message, bot: Bot):
    """Bot egasining guruhga yuborgan qo'shilish so'rovini qabul qilishga urinish."""
    if not is_bot_owner(message.from_user):
        return

    from group_bot.database import get_connection
    user_id = message.from_user.id
    chat_ids = set()
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT DISTINCT chat_id FROM chats WHERE chat_id < 0")
            for r in cur.fetchall():
                chat_ids.add(r[0])
            cur = conn.execute("SELECT DISTINCT chat_id FROM chat_settings WHERE chat_id < 0")
            for r in cur.fetchall():
                chat_ids.add(r[0])
    except Exception:
        pass

    if not chat_ids:
        chat_ids.add(-1003834509976)

    success_chats = []
    failed_chats = []

    for cid in chat_ids:
        try:
            await bot.approve_chat_join_request(chat_id=cid, user_id=user_id)
            try:
                chat_info = await bot.get_chat(cid)
                c_title = chat_info.title or str(cid)
            except Exception:
                c_title = str(cid)
            success_chats.append(c_title)
        except Exception as e:
            failed_chats.append((cid, str(e)))

    if success_chats:
        text = "✅ <b>Quyidagi guruhlarga qo‘shilish so‘rovingiz qabul qilindi:</b>\n\n" + "\n".join(f"• <b>{c}</b>" for c in success_chats)
    else:
        text = "❌ <b>So‘rovingizni hozircha qabul qilib bo‘lmadi!</b>\n\n"
        err_msg = failed_chats[0][1] if failed_chats else "Noma’lum"
        if "not enough rights" in err_msg.lower():
            text += (
                "⚠️ <b>Telegram cheklovi:</b> Botda guruhda <b>«Foydalanuvchilarni taklif qilish» (can_invite_users)</b> adminlik huquqi o‘chirilgan.\n\n"
                "Telegram qoidasiga binoan, faqat ushbu huquqqa ega admin botlargina a'zolarni qabul qila oladi.\n"
                "<i>Iltimos, guruh egasidan (@mrzklvv18) botga shu huquqni berishini yoki Telegramdagi «So‘rovlar» ro‘yxatidan so‘rovingizni tasdiqlashini so‘rang.</i>"
            )
        else:
            text += f"Sabab: <code>{escape(err_msg)}</code>"

    await message.reply(text, parse_mode="HTML")




