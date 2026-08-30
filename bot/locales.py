# Multi-Language Localization Dictionary for FilmFinder Bot

MESSAGES = {
    "uz": {
        "choose_lang": "🌐 <b>Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please choose a language:</b>",
        "welcome": (
            "Assalomu alaykum, <b>{name}</b>! 👋\n\n"
            "🎬 <b>AI Movie Finder Bot</b> ga xush kelibsiz!\n\n"
            "Men sizga <b>Instagram Reels</b>, <b>YouTube Shorts</b> yoki to'g'ridan-to'g'ri yuborilgan "
            "videolardan <b>qaysi kino, serial, anime yoki multfilm</b> ekanligini real vaqtda aniqlab beraman! 🤖✨\n\n"
            "🔥 <b>Qanday ishlatiladi?</b>\n"
            "1️⃣ O'zingizga yoqqan video havolasini (Instagram Reels, YouTube Shorts) bu yerga yuboring.\n"
            "2️⃣ Yoki to'g'ridan-to'g'ri videoni yuboring.\n"
            "3️⃣ Bot bir necha soniya ichida film nomini, aktyorlarini, treylerini va premyera holatini aytib beradi!\n\n"
            "🚀 <i>Hoziroq birorta havola yoki video yuborib sinab ko'ring!</i>"
        ),
        "help": (
            "💡 <b>Botdan foydalanish bo'yicha yordam:</b>\n\n"
            "📌 <b>Qo'llab-quvvatlanadigan manbalar:</b>\n"
            "• 📸 <b>Instagram Reels</b> va postlar\n"
            "• 🔴 <b>YouTube Shorts</b> va videolar\n"
            "• 📁 <b>Telegram videolari</b> va video xabarlar\n\n"
            "⚡️ <b>Premyera filmlar:</b>\n"
            "Agar film hali kinoteatrlarda chiqmagan bo'lsa, bot buni aniqlab, kutilayotgan premyera sanasini ko'rsatadi.\n\n"
            "🌐 Tilni o'zgartirish uchun /lang buyrug'idan foydalaning.\n\n"
            "👨‍💻 <b>Aloqa va takliflar:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>AI FilmFinder haqida</b>\n\n"
            "Ushbu bot — ijtimoiy tarmoqlardagi qisqa videolardan kinolarni bir zumda topib beruvchi aqlli yordamchingizdir! ✨\n\n"
            "🌟 <b>Asosiy imkoniyatlar:</b>\n"
            "• 🎞 <b>Tezkor qidiruv:</b> Instagram Reels va YouTube Shorts lavhalaridan kinoni aniqlash\n"
            "• 🎥 <b>Premyeralar:</b> Hali chiqmagan filmlar va ularning chiqish sanasini bilish\n"
            "• 🍿 <b>Treylerlar:</b> Rasmiy treylerni bir bosishda YouTube orqali tomosha qilish\n"
            "• 👥 <b>Qahramonlar va sujet:</b> Bosh rollar va film mazmuni bilan tanishish\n\n"
            "📩 <b>Reklama va hamkorlik uchun:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Admin / Dasturchi:</b> @khojayev_ramz\n\n"
            "❤️ <i>Botingizni do'stlaringizga ham ulashing!</i>"
        ),
        "status_downloading": "⏳ <b>Video qabul qilindi! Yuklab olinmoqda...</b>\n<i>(Bir necha soniya vaqt olishi mumkin)</i>",
        "status_analyzing": "🧠 <b>Sun'iy intellekt videoni ko'rib tahlil qilmoqda...</b>\n<i>(Kadrlar, aktyorlar, dialoglar va sahna o'rganilmoqda)</i>",
        "status_db": "🎬 <b>Kino bazasidan ma'lumotlar jamlanmoqda...</b>",
        "error_download": (
            "❌ <b>Videoni yuklab bo'lmadi!</b>\n\n"
            "• Havola to'g'riligini tekshiring.\n"
            "• Video shaxsiy (private) yoki yopiq profilda emasligiga ishonch hosil qiling.\n"
            "• Yoki videoni to'g'ridan-to'g'ri fayl ko'rinishida yuboring."
        ),
        "error_not_found": (
            "😔 <b>Afsuski, film/serialni aniqlab bo'lmadi.</b>\n\n"
            "ℹ️ <b>Sababi:</b> {reason}\n\n"
            "💡 <i>Maslahat: Videoda kino qahramonlari, yuzlari yoki taniqli sahnalar ko'proq aks etgan qismini yuborishga harakat qiling.</i>"
        ),
        "error_general": "⚠️ <i>Kechirasiz, videoni tahlil qilishda kutilmagan xatolik yuz berdi. Qayta urinib ko'ring.</i>",
        "send_prompt": "Iltimos, video havolasini (Instagram Reels, YouTube Shorts) yuboring yoki to'g'ridan-to'g'ri videoni tashlang! 🎬",
        "btn_trailer": "🎬 Rasmiy Treyler (YouTube)",
        "btn_trailer_search": "🎬 Treylerni qidirish",
        "btn_imdb": "⭐️ IMDb sahifasi",
        "btn_kinopoisk": "🍿 Kinopoisk",
        "btn_tmdb": "🌐 TMDb sahifasi",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Do'stlarga ulashish",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_contact_admin": "👨‍💻 Bog'lanish / Aloqa",
        "lang_changed": "✅ Til <b>O'zbekcha</b>ga o'zgartirildi!",
        "share_text": "Men ushbu kinoni topdim: {title} 🎬",
        "type_movie": "🎬 <b>Film / Kino</b>",
        "type_series": "📺 <b>Serial / Dorama</b>",
        "type_cartoon": "🎨 <b>Multfilm / Animatsiya</b>",
        "type_anime": "🌸 <b>Anime</b>",
        "type_trailer": "🎥 <b>Rasmiy Treyler / Teaser</b>",
        "label_type": "📌 <b>Turi:</b>",
        "label_premiere": "🔥 <b>Holati:</b> 🔴 <b>Hali chiqarilmagan / PREMYERA</b>",
        "label_year": "📅 <b>Yili:</b>",
        "label_rating": "⭐ <b>Reyting:</b>",
        "label_genres": "🎭 <b>Janr:</b>",
        "label_actors": "👥 <b>Bosh rollarda:</b>",
        "label_scene": "🔎 <b>Videodagi sahna:</b>",
        "label_summary": "📖 <b>Qisqacha mazmuni:</b>",
        "label_found_by": "🤖 <i>Topildi: AI Vision Engine</i>"
    },

    "uz_kr": {
        "choose_lang": "🌐 <b>Илтимос, тилни танланг / Пожалуйста, выберите язык / Please choose a language:</b>",
        "welcome": (
            "Ассалому алайкум, <b>{name}</b>! 👋\n\n"
            "🎬 <b>AI Movie Finder Bot</b> га хуш келибсиз!\n\n"
            "Мен сизга <b>Instagram Reels</b>, <b>YouTube Shorts</b> ёки тўғридан-тўғри юборилган "
            "видеолардан <b>қайси кино, сериал, аниме ёки мультфильм</b> эканлигини реал вақтда аниқлаб бераман! 🤖✨\n\n"
            "🔥 <b>Қандай ишлатилади?</b>\n"
            "1️⃣ Ўзингизга ёққан видео ҳаволасини (Instagram Reels, YouTube Shorts) бу ерга юборинг.\n"
            "2️⃣ Ёки тўғридан-тўғри видеони юборинг.\n"
            "3️⃣ Бот бир неча сония ичида фильм номини, актёрларини, трейлерини ва премьера ҳолатини айтиб беради!\n\n"
            "🚀 <i>Ҳозироқ бирорта ҳавола ёки видео юбориб синаб кўринг!</i>"
        ),
        "help": (
            "💡 <b>Ботдан фойдаланиш бўйича ёрдам:</b>\n\n"
            "📌 <b>Қўллаб-қувватланадиган манбалар:</b>\n"
            "• 📸 <b>Instagram Reels</b> ва постлар\n"
            "• 🔴 <b>YouTube Shorts</b> ва видеолар\n"
            "• 📁 <b>Telegram видеолари</b> ва думалоқ видеолар\n\n"
            "⚡️ <b>Премьера фильмлар:</b>\n"
            "Агар фильм ҳали кинотеатрларда чиқмаган бўлса, бот буни аниқлаб, кутилаётган премьера санасини кўрсатади.\n\n"
            "🌐 Тилни ўзгартириш учун /lang буйруғидан фойдаланинг.\n\n"
            "👨‍💻 <b>Алоқа ва таклифлар:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>AI FilmFinder ҳақида</b>\n\n"
            "Ушбу бот — ижтимоий тармоқлардаги қисқа видеолардан киноларни бир зумда топиб берувчи ақлли ёрдамчингиздир! ✨\n\n"
            "🌟 <b>Асосий имкониятлар:</b>\n"
            "• 🎞 <b>Тезкор қидирув:</b> Instagram Reels ва YouTube Shorts лавҳаларидан кинони аниқлаш\n"
            "• 🎥 <b>Премьералар:</b> Ҳали чиқмаган фильмлар ва уларнинг чиқиш санасини билиш\n"
            "• 🍿 <b>Трейлерлар:</b> Расмий трейлерни бир босишда YouTube орқали томоша қилиш\n"
            "• 👥 <b>Қаҳрамонлар ва сюжет:</b> Бош роллар ва фильм мазмуни билан танишиш\n\n"
            "📩 <b>Реклама ва ҳамкорлик учун:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Админ:</b> @khojayev_ramz\n\n"
            "❤️ <i>Ботингизни дўстларингизга ҳам улашинг!</i>"
        ),
        "status_downloading": "⏳ <b>Видео қабул қилинди! Юклаб олинмоқда...</b>\n<i>(Бир неча сония вақт олиши мумкин)</i>",
        "status_analyzing": "🧠 <b>Сунъий интеллект видеони кўриб таҳлил қилмоқда...</b>\n<i>(Кадрлар, актёрлар, диалоглар ва саҳна ўрганилмоқда)</i>",
        "status_db": "🎬 <b>Кино базасидан маълумотлар жамланмоқда...</b>",
        "error_download": (
            "❌ <b>Videoni юклаб бўлмади!</b>\n\n"
            "• Ҳавола тўғрилигини текширинг.\n"
            "• Видео шахсий (private) ёки ёпиқ профилда эмаслигига ишонч ҳосил қилинг.\n"
            "• Ёки видеони тўғридан-тўғри файл кўринишида юборинг."
        ),
        "error_not_found": (
            "😔 <b>Афсуски, фильм/сериални аниқлаб бўлмади.</b>\n\n"
            "ℹ️ <b>Сабаби:</b> {reason}\n\n"
            "💡 <i>Маслаҳат: Видеода кино қаҳрамонлари, юзлари ёки таниқли саҳналар кўпроқ акс этган қисмини юборишга ҳаракат қилинг.</i>"
        ),
        "error_general": "⚠️ <i>Кечирасиз, видеони таҳлил қилишда кутилмаган хатолик юз берди. Қайта уриниб кўринг.</i>",
        "send_prompt": "Илтимос, видео ҳаволасини (Instagram Reels, YouTube Shorts) юборинг ёки тўғридан-тўғри видеони ташланг! 🎬",
        "btn_trailer": "🎬 Расмий Трейлер (YouTube)",
        "btn_trailer_search": "🎬 Трейлерни қидириш",
        "btn_imdb": "⭐️ IMDb саҳифаси",
        "btn_kinopoisk": "🍿 Кинопоиск",
        "btn_tmdb": "🌐 TMDb саҳифаси",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Дўстларга улашиш",
        "btn_change_lang": "🌐 Тилни ўзгартириш",
        "btn_contact_admin": "👨‍💻 Боғланиш / Алоқа",
        "lang_changed": "✅ Тил <b>Ўзбекча (Кирилл)</b>га ўзгартирилди!",
        "share_text": "Мен ушбу кинони топдим: {title} 🎬",
        "type_movie": "🎬 <b>Фильм / Кино</b>",
        "type_series": "📺 <b>Сериал / Дорама</b>",
        "type_cartoon": "🎨 <b>Мультфильм / Анимация</b>",
        "type_anime": "🌸 <b>Аниме</b>",
        "type_trailer": "🎥 <b>Расмий Трейлер / Тизер</b>",
        "label_type": "📌 <b>Тури:</b>",
        "label_premiere": "🔥 <b>Ҳолати:</b> 🔴 <b>Ҳали чиқарилмаган / ПРЕМЬЕРА</b>",
        "label_year": "📅 <b>Йили:</b>",
        "label_rating": "⭐ <b>Рейтинг:</b>",
        "label_genres": "🎭 <b>Жанр:</b>",
        "label_actors": "👥 <b>Бош ролларда:</b>",
        "label_scene": "🔎 <b>Видеодаги саҳна:</b>",
        "label_summary": "📖 <b>Қисқача мазмуни:</b>",
        "label_found_by": "🤖 <i>Топилди: AI Vision Engine</i>"
    },

    "ru": {
        "choose_lang": "🌐 <b>Пожалуйста, выберите язык / Please choose a language / Tilni tanlang:</b>",
        "welcome": (
            "Здравствуйте, <b>{name}</b>! 👋\n\n"
            "🎬 Добро пожаловать в <b>AI Movie Finder Bot</b>!\n\n"
            "Я помогу вам мгновенно распознать <b>фильм, сериал, аниме или мультфильм</b> "
            "по ссылке из <b>Instagram Reels</b>, <b>YouTube Shorts</b> или прямому видео! 🤖✨\n\n"
            "🔥 <b>Как пользоваться?</b>\n"
            "1️⃣ Отправьте ссылку на видео (Instagram Reels, YouTube Shorts).\n"
            "2️⃣ Или просто отправьте сам видеофайл.\n"
            "3️⃣ Бот за несколько секунд назовет фильм, покажет актеров, трейлер и статус премьеры!\n\n"
            "🚀 <i>Отправьте ссылку или видео прямо сейчас!</i>"
        ),
        "help": (
            "💡 <b>Помощь по использованию:</b>\n\n"
            "📌 <b>Поддерживаемые источники:</b>\n"
            "• 📸 <b>Instagram Reels</b> и публикации\n"
            "• 🔴 <b>YouTube Shorts</b> и видео\n"
            "• 📁 <b>Видеофайлы</b> и видеосообщения из Telegram\n\n"
            "⚡️ <b>Премьеры:</b>\n"
            "Если фильм еще не вышел в прокат, бот укажет точную дату ожидаемой премьеры.\n\n"
            "🌐 Для смены языка используйте команду /lang.\n\n"
            "👨‍💻 <b>Связь и реклама:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>О боте AI FilmFinder</b>\n\n"
            "Этот бот — ваш умный помощник для мгновенного поиска фильмов и сериалов из коротких видеороликов! ✨\n\n"
            "🌟 <b>Возможности:</b>\n"
            "• 🎞 <b>Быстрый поиск:</b> Распознавание фильмов по отрывкам из Reels и Shorts\n"
            "• 🎥 <b>Премьеры:</b> Информация о готовящихся к выходу фильмах и датах релиза\n"
            "• 🍿 <b>Трейлеры:</b> Просмотр официальных трейлеров на YouTube в один клик\n"
            "• 👥 <b>Актеры и сюжет:</b> Главные роли и краткое содержание фильма\n\n"
            "📩 <b>По вопросам рекламы и сотрудничества:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Администратор:</b> @khojayev_ramz\n\n"
            "❤️ <i>Делитесь ботом с друзьями!</i>"
        ),
        "status_downloading": "⏳ <b>Видео получено! Загрузка...</b>\n<i>(Это займет пару секунд)</i>",
        "status_analyzing": "🧠 <b>Искусственный интеллект анализирует видео...</b>\n<i>(Изучаются кадры, актеры, диалоги и сцена)</i>",
        "status_db": "🎬 <b>Поиск подробной информации...</b>",
        "error_download": (
            "❌ <b>Не удалось скачать видео!</b>\n\n"
            "• Проверьте правильность ссылки.\n"
            "• Убедитесь, что видео не находится в приватном/закрытом профиле.\n"
            "• Или отправьте видео напрямую файлом."
        ),
        "error_not_found": (
            "😔 <b>К сожалению, фильм/сериал не удалось распознать.</b>\n\n"
            "ℹ️ <b>Причина:</b> {reason}\n\n"
            "💡 <i>Совет: Попробуйте отправить фрагмент, где лучше видны лица персонажей или ключевые сцены.</i>"
        ),
        "error_general": "⚠️ <i>Извините, произошла непредвиденная ошибка при анализе. Попробуйте еще раз.</i>",
        "send_prompt": "Пожалуйста, отправьте ссылку на видео (Instagram Reels, YouTube Shorts) или само видео! 🎬",
        "btn_trailer": "🎬 Официальный трейлер (YouTube)",
        "btn_trailer_search": "🎬 Искать трейлер",
        "btn_imdb": "⭐️ Страница на IMDb",
        "btn_kinopoisk": "🍿 Кинопоиск",
        "btn_tmdb": "🌐 Страница на TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Поделиться с друзьями",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_contact_admin": "👨‍💻 Связаться с админом",
        "lang_changed": "✅ Язык успешно изменен на <b>Русский</b>!",
        "share_text": "Я нашел этот фильм: {title} 🎬",
        "type_movie": "🎬 <b>Фильм / Кино</b>",
        "type_series": "📺 <b>Сериал / Дорама</b>",
        "type_cartoon": "🎨 <b>Мультфильм / Анимация</b>",
        "type_anime": "🌸 <b>Аниме</b>",
        "type_trailer": "🎥 <b>Официальный трейлер / Тизер</b>",
        "label_type": "📌 <b>Тип:</b>",
        "label_premiere": "🔥 <b>Статус:</b> 🔴 <b>Еще не вышел / ПРЕМЬЕРА</b>",
        "label_year": "📅 <b>Год:</b>",
        "label_rating": "⭐ <b>Рейтинг:</b>",
        "label_genres": "🎭 <b>Жанр:</b>",
        "label_actors": "👥 <b>В главных ролях:</b>",
        "label_scene": "🔎 <b>Сцена из видео:</b>",
        "label_summary": "📖 <b>Краткий сюжет:</b>",
        "label_found_by": "🤖 <i>Найдено: AI Vision Engine</i>"
    },

    "en": {
        "choose_lang": "🌐 <b>Please choose your language / Iltimos, tilni tanlang / Выберите язык:</b>",
        "welcome": (
            "Hello, <b>{name}</b>! 👋\n\n"
            "🎬 Welcome to <b>AI Movie Finder Bot</b>!\n\n"
            "I can identify any <b>movie, TV show, anime, or animated cartoon</b> in real-time from "
            "<b>Instagram Reels</b>, <b>YouTube Shorts</b>, or direct video files! 🤖✨\n\n"
            "🔥 <b>How to use:</b>\n"
            "1️⃣ Send a video link (Instagram Reels, YouTube Shorts).\n"
            "2️⃣ Or directly upload the video file.\n"
            "3️⃣ Within seconds, I will tell you the title, cast, official trailer, and premiere status!\n\n"
            "🚀 <i>Send a link or video now to try it out!</i>"
        ),
        "help": (
            "💡 <b>Help & Guide:</b>\n\n"
            "📌 <b>Supported Platforms:</b>\n"
            "• 📸 <b>Instagram Reels</b> & Posts\n"
            "• 🔴 <b>YouTube Shorts</b> & Videos\n"
            "• 📁 <b>Direct Video Files</b> & Video Notes from Telegram\n\n"
            "⚡️ <b>Upcoming Premieres:</b>\n"
            "If the movie is not yet released, the bot will state that and provide the expected release date.\n\n"
            "🌐 Use /lang to change your language anytime.\n\n"
            "👨‍💻 <b>Contact & Support:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>About AI FilmFinder</b>\n\n"
            "This bot is your smart AI companion for instantly finding movies and TV shows from short video clips! ✨\n\n"
            "🌟 <b>Key Features:</b>\n"
            "• 🎞 <b>Instant Recognition:</b> Identify movies from Instagram Reels & YouTube Shorts\n"
            "• 🎥 <b>Upcoming Premieres:</b> Discover unreleased movies and their official release dates\n"
            "• 🍿 <b>Official Trailers:</b> Watch official YouTube trailers with a single tap\n"
            "• 👥 <b>Cast & Plot:</b> Explore cast lists and concise storyline summaries\n\n"
            "📩 <b>For ads and inquiries:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Admin / Developer:</b> @khojayev_ramz\n\n"
            "❤️ <i>Finding your favorite movies has never been easier! Share with your friends!</i>"
        ),
        "status_downloading": "⏳ <b>Video received! Downloading...</b>\n<i>(This takes a few seconds)</i>",
        "status_analyzing": "🧠 <b>AI is analyzing the video frames & audio...</b>\n<i>(Examining characters, actors, dialogue, and scene context)</i>",
        "status_db": "🎬 <b>Fetching movie metadata...</b>",
        "error_download": (
            "❌ <b>Could not download video!</b>\n\n"
            "• Make sure the URL is valid.\n"
            "• Ensure the video is public and not from a private account.\n"
            "• Or upload the video file directly."
        ),
        "error_not_found": (
            "😔 <b>Sorry, could not recognize the movie or series.</b>\n\n"
            "ℹ️ <b>Reason:</b> {reason}\n\n"
            "💡 <i>Tip: Try sending a clip showing clear character faces or memorable scenes.</i>"
        ),
        "error_general": "⚠️ <i>Sorry, an unexpected error occurred while analyzing. Please try again.</i>",
        "send_prompt": "Please send a video link (Instagram Reels, YouTube Shorts) or upload a video directly! 🎬",
        "btn_trailer": "🎬 Official Trailer (YouTube)",
        "btn_trailer_search": "🎬 Search Trailer",
        "btn_imdb": "⭐️ IMDb Page",
        "btn_kinopoisk": "🍿 Kinopoisk",
        "btn_tmdb": "🌐 TMDb Page",
        "btn_google": "🔍 Google Search",
        "btn_share": "↗️ Share with Friends",
        "btn_change_lang": "🌐 Change Language",
        "btn_contact_admin": "👨‍💻 Contact Admin",
        "lang_changed": "✅ Language changed to <b>English</b>!",
        "share_text": "I found this movie: {title} 🎬",
        "type_movie": "🎬 <b>Movie / Film</b>",
        "type_series": "📺 <b>TV Series / Drama</b>",
        "type_cartoon": "🎨 <b>Animation / Cartoon</b>",
        "type_anime": "🌸 <b>Anime</b>",
        "type_trailer": "🎥 <b>Official Trailer / Teaser</b>",
        "label_type": "📌 <b>Type:</b>",
        "label_premiere": "🔥 <b>Status:</b> 🔴 <b>Not Yet Released / PREMIERE</b>",
        "label_year": "📅 <b>Year:</b>",
        "label_rating": "⭐ <b>Rating:</b>",
        "label_genres": "🎭 <b>Genres:</b>",
        "label_actors": "👥 <b>Cast:</b>",
        "label_scene": "🔎 <b>Scene Context:</b>",
        "label_summary": "📖 <b>Summary:</b>",
        "label_found_by": "🤖 <i>Identified by: AI Vision Engine</i>"
    }
}


def get_msg(lang: str, key: str, **kwargs) -> str:
    """Retrieves a localized string with optional formatting."""
    lang_dict = MESSAGES.get(lang, MESSAGES["uz"])
    text = lang_dict.get(key, MESSAGES["uz"].get(key, ""))
    if kwargs and text:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
