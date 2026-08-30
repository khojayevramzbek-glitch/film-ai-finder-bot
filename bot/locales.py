# Multi-Language Localization Dictionary for FilmFinder Bot

MESSAGES = {
    "uz": {
        "choose_lang": "🌐 <b>Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please choose a language:</b>",
        "welcome": (
            "Assalomu alaykum, <b>{name}</b>! 👋\n\n"
            "🎬 <b>AI Movie Finder Bot</b> ga xush kelibsiz!\n\n"
            "Men sizga 3 xil usulda istalgan <b>kino, serial, anime yoki multfilmni</b> soniyalar ichida topib beraman: 🤖✨\n\n"
            "1️⃣ <b>Video orqali:</b> Instagram Reels, YouTube Shorts yoki to'g'ridan-to'g'ri video yuboring.\n"
            "2️⃣ <b>Skrinshot orqali:</b> Kinodan olingan bitta rasm/foto yuboring.\n"
            "3️⃣ <b>Matn orqali:</b> Kino nomini eslay olmasangiz, esingizda qolgan voqeani yozing (masalan: <i>\"Bitta kishi orolda to'p bilan qolib ketadi\"</i>).\n\n"
            "🎲 Nima ko'rishni bilmayotgan bo'lsangiz, /random buyrug'ini bosing!\n\n"
            "🚀 <i>Hoziroq birorta havola, rasm yoki matn yuborib sinab ko'ring!</i>"
        ),
        "help": (
            "💡 <b>Botdan foydalanish bo'yicha yordam:</b>\n\n"
            "🔍 <b>Qidiruv imkoniyatlari:</b>\n"
            "• 📸 <b>Instagram Reels & YouTube Shorts</b> havolalari\n"
            "• 📁 <b>Telegram videolari</b> va video xabarlar\n"
            "• 🖼 <b>Skrinshot / Rasmlar</b>: Kinodan olingan fotoni yuboring\n"
            "• 📝 <b>Syujet bo'yicha qidiruv</b>: Kinoda nima bo'lganini oddiy so'zlar bilan yozing\n\n"
            "🎲 <b>Maxsus buyruqlar:</b>\n"
            "• /random — Bugun nima ko'rsam ekan? (Janrlar bo'yicha eng zo'r kinolar)\n"
            "• /lang — Tilni o'zgartirish\n"
            "• /about — Bot haqida va aloqa\n\n"
            "👨‍💻 <b>Aloqa va takliflar:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>AI FilmFinder haqida</b>\n\n"
            "Ushbu bot — sun'iy intellekt orqali videolardan, skrinshotlardan va matnli ta'riflardan kinolarni bir zumda topib beruvchi aqlli yordamchingizdir! ✨\n\n"
            "🌟 <b>Asosiy imkoniyatlar:</b>\n"
            "• 🎞 <b>Tezkor qidiruv:</b> Reels, Shorts, Foto va Matn orqali kinoni topish\n"
            "• 🎥 <b>Premyeralar:</b> Hali chiqmagan filmlar va ularning chiqish sanasini bilish\n"
            "• 🍿 <b>Treylerlar & Onlayn ko'rish:</b> YouTube treylerlari va tarjima kino havolalari\n"
            "• 🎭 <b>O'xshash kinolar:</b> Har bir filmga mos tavsiyalar\n"
            "• 🎲 <b>Tasodifiy TOP kinolar:</b> Janr bo'yicha eng zo'r filmlar tavsiyasi\n\n"
            "📩 <b>Reklama va hamkorlik uchun:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Admin / Dasturchi:</b> @khojayev_ramz\n\n"
            "❤️ <i>Botingizni do'stlaringizga ham ulashing!</i>"
        ),
        "status_downloading": "⏳ <b>Video qabul qilindi! Yuklab olinmoqda...</b>\n<i>(Bir necha soniya vaqt olishi mumkin)</i>",
        "status_analyzing": "🧠 <b>Sun'iy intellekt videoni ko'rib tahlil qilmoqda...</b>\n<i>(Kadrlar, aktyorlar, dialoglar va sahna o'rganilmoqda)</i>",
        "status_photo_search": "🧠 <b>Sun'iy intellekt rasm/skrinshotni tahlil qilmoqda...</b>\n<i>(Qahramonlar, sahna va liboslar o'rganilmoqda)</i>",
        "status_plot_search": "🧠 <b>Sun'iy intellekt syujet bo'yicha kinoni qidirmoqda...</b>\n<i>(Kino bazasi va syujet solishtirilmoqda)</i>",
        "status_similar_search": "🎭 <b>Shunga o'xshash eng sara filmlar saralanmoqda...</b>",
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
            "💡 <i>Maslahat: Kinodagi asosiy qahramonlar, sahna yoki voqeani aniqroq yozishga/yuborishga harakat qiling.</i>"
        ),
        "error_general": "⚠️ <i>Kechirasiz, kutilmagan xatolik yuz berdi. Qayta urinib ko'ring.</i>",
        "send_prompt": "Iltimos, video havolasi (Reels/Shorts), skrinshot yoki film voqeasini matn ko'rinishida yuboring! 🎬",
        "btn_trailer": "🎬 Rasmiy Treyler (YouTube)",
        "btn_trailer_search": "🎬 Treylerni qidirish",
        "btn_watch_uz": "🍿 O'zbek tilida ko'rish",
        "btn_similar": "🎭 Shunga o'xshash filmlar",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Kinopoisk",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Do'stlarga ulashish",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_contact_admin": "👨‍💻 Bog'lanish / Aloqa",
        "btn_random_more": "🔄 Boshqa kino tavsiya qilish",
        "btn_back_genres": "🔙 Janrlar ro'yxati",
        "random_choose_genre": "🎲 <b>Bugun qanday janrdagi film ko'rmoqchisiz? Janrni tanlang:</b>",
        "genre_action": "💥 Jangari (Action)",
        "genre_comedy": "😂 Komediya",
        "genre_scifi": "🚀 Fantastika & Kosmos",
        "genre_horror": "😱 Dahshat & Qo'rqinchli",
        "genre_drama": "🎭 Drama & Hayotiy",
        "genre_cartoon": "🎨 Multfilm & Oila",
        "genre_anime": "🌸 Anime",
        "lang_changed": "✅ Til <b>O'zbekcha</b>ga o'zgartirildi!",
        "share_text": "Men ushbu ajoyib kinoni topdim: {title} 🎬",
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
        "label_why_watch": "💡 <b>Nima uchun ko'rish kerak:</b>",
        "label_found_by": "🤖 <i>Topildi: AI Vision & Plot Engine</i>"
    },

    "uz_kr": {
        "choose_lang": "🌐 <b>Илтимос, тилни танланг / Пожалуйста, выберите язык / Please choose a language:</b>",
        "welcome": (
            "Ассалому алайкум, <b>{name}</b>! 👋\n\n"
            "🎬 <b>AI Movie Finder Bot</b> га хуш келибсиз!\n\n"
            "Мен сизга 3 хил усулда исталган <b>кино, сериал, аниме ёки мультфильмни</b> сониялар ичида топиб бераман: 🤖✨\n\n"
            "1️⃣ <b>Видео орқали:</b> Instagram Reels, YouTube Shorts ёки тўғридан-тўғри видео юборинг.\n"
            "2️⃣ <b>Скриншот орқали:</b> Кинодан олинган битта расм/фото юборинг.\n"
            "3️⃣ <b>Матн орқали:</b> Кино номини эслай олмасангиз, эсингизда қолган воқеани ёзинг (масалан: <i>\"Битта киши оролда тўп билан қолиб кетади\"</i>).\n\n"
            "🎲 Нима кўришни билмаётган бўлсангиз, /random буйруғини босинг!\n\n"
            "🚀 <i>Ҳозироқ бирорта ҳавола, расм ёки матн юбориб синаб кўринг!</i>"
        ),
        "help": (
            "💡 <b>Ботдан фойдаланиш бўйича ёрдам:</b>\n\n"
            "🔍 <b>Қидирув имкониятлари:</b>\n"
            "• 📸 <b>Instagram Reels & YouTube Shorts</b> ҳаволалари\n"
            "• 📁 <b>Telegram видеолари</b> ва видео хабарлар\n"
            "• 🖼 <b>Скриншот / Расмлар</b>: Кинодан олинган фотони юборинг\n"
            "• 📝 <b>Сюжет бўйича қидирув</b>: Кинода нима бўлганини оддий сўзлар билан ёзинг\n\n"
            "🎲 <b>Махсус буйруқлар:</b>\n"
            "• /random — Бугун нима кўрсам экан? (Жанрлар бўйича энг зўр кинолар)\n"
            "• /lang — Тилни ўзгартириш\n"
            "• /about — Бот ҳақида ва алоқа\n\n"
            "👨‍💻 <b>Алоқа ва таклифлар:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>AI FilmFinder ҳақида</b>\n\n"
            "Ушбу бот — сунъий интеллект орқали видеолардан, скриншотлардан ва матнли таърифлардан киноларни бир зумда топиб берувчи ақлли ёрдамчингиздир! ✨\n\n"
            "🌟 <b>Асосий имкониятлар:</b>\n"
            "• 🎞 <b>Тезкор қидирув:</b> Reels, Shorts, Фото ва Матн орқали кинони топиш\n"
            "• 🎥 <b>Премьералар:</b> Ҳали чиқмаган фильмлар ва уларнинг чиқиш санасини билиш\n"
            "• 🍿 <b>Трейлерлар & Онлайн кўриш:</b> YouTube трейлерлари ва таржима кино ҳаволалари\n"
            "• 🎭 <b>Ўхшаш кинолар:</b> Ҳар бир фильмга мос тавсиялар\n"
            "• 🎲 <b>Тасодифий ТОП кинолар:</b> Жанр бўйича энг зўр фильмлар тавсияси\n\n"
            "📩 <b>Реклама ва ҳамкорлик учун:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Админ:</b> @khojayev_ramz\n\n"
            "❤️ <i>Ботингизни дўстларингизга ҳам улашинг!</i>"
        ),
        "status_downloading": "⏳ <b>Видео қабул қилинди! Юклаб олинмоқда...</b>\n<i>(Бир неча сония вақт олиши мумкин)</i>",
        "status_analyzing": "🧠 <b>Сунъий интеллект видеони кўриб таҳлил қилмоқда...</b>\n<i>(Кадрлар, актёрлар, диалоглар ва саҳна ўрганилмоқда)</i>",
        "status_photo_search": "🧠 <b>Сунъий интеллект расм/скриншотни таҳлил қилмоқда...</b>\n<i>(Қаҳрамонлар, саҳна ва либослар ўрганилмоқда)</i>",
        "status_plot_search": "🧠 <b>Сунъий интеллект сюжет бўйича кинони қидирмоқда...</b>\n<i>(Кино базаси ва сюжет солиштирилмоқда)</i>",
        "status_similar_search": "🎭 <b>Шунга ўхшаш энг сара фильмлар сараланмоқда...</b>",
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
            "💡 <i>Маслаҳат: Кинодаги асосий қаҳрамонлар, саҳна ёки воқеани аниқроқ ёзишга/юборишга ҳаракат қилинг.</i>"
        ),
        "error_general": "⚠️ <i>Кечирасиз, кутилмаган хатолик юз берди. Қайта уриниб кўринг.</i>",
        "send_prompt": "Илтимос, видео ҳаволаси (Reels/Shorts), скриншот ёки фильм воқеасини матн кўринишида юборинг! 🎬",
        "btn_trailer": "🎬 Расмий Трейлер (YouTube)",
        "btn_trailer_search": "🎬 Трейлерни қидириш",
        "btn_watch_uz": "🍿 Ўзбек тилида кўриш",
        "btn_similar": "🎭 Шунга ўхшаш фильмлар",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Кинопоиск",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Дўстларга улашиш",
        "btn_change_lang": "🌐 Тилни ўзгартириш",
        "btn_contact_admin": "👨‍💻 Боғланиш / Алоқа",
        "btn_random_more": "🔄 Бошқа кино тавсия қилиш",
        "btn_back_genres": "🔙 Жанрлар рўйхати",
        "random_choose_genre": "🎲 <b>Бугун қандай жанрдаги фильм кўрмоқчисиз? Жанрни танланг:</b>",
        "genre_action": "💥 Жангари (Action)",
        "genre_comedy": "😂 Комедия",
        "genre_scifi": "🚀 Фантастика & Космос",
        "genre_horror": "😱 Даҳшат & Қўрқинчли",
        "genre_drama": "🎭 Драма & Ҳаётий",
        "genre_cartoon": "🎨 Мультфильм & Оила",
        "genre_anime": "🌸 Аниме",
        "lang_changed": "✅ Тил <b>Ўзбекча (Кирилл)</b>га ўзгартирилди!",
        "share_text": "Мен ушбу ажойиб кинони топдим: {title} 🎬",
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
        "label_why_watch": "💡 <b>Нима учун кўриш керак:</b>",
        "label_found_by": "🤖 <i>Топилди: AI Vision & Plot Engine</i>"
    },

    "ru": {
        "choose_lang": "🌐 <b>Пожалуйста, выберите язык / Please choose a language / Tilni tanlang:</b>",
        "welcome": (
            "Здравствуйте, <b>{name}</b>! 👋\n\n"
            "🎬 Добро пожаловать в <b>AI Movie Finder Bot</b>!\n\n"
            "Я помогу вам мгновенно распознать любой <b>фильм, сериал, аниме или мультфильм</b> 3 удобными способами: 🤖✨\n\n"
            "1️⃣ <b>По видео:</b> Отправьте ссылку на Instagram Reels, YouTube Shorts или сам видеофайл.\n"
            "2️⃣ <b>По скриншоту:</b> Отправьте фото или скриншот кадра из фильма.\n"
            "3️⃣ <b>По сюжету:</b> Если забыли название, просто опишите сюжет своими словами (например: <i>\"Человек остался один на необитаемом острове с мячом\"</i>).\n\n"
            "🎲 Не знаете, что посмотреть? Нажмите /random!\n\n"
            "🚀 <i>Отправьте ссылку, фото или текст прямо сейчас!</i>"
        ),
        "help": (
            "💡 <b>Помощь и возможности:</b>\n\n"
            "🔍 <b>Способы поиска:</b>\n"
            "• 📸 <b>Instagram Reels & YouTube Shorts</b> ссылки\n"
            "• 📁 <b>Видеофайлы</b> и кружочки из Telegram\n"
            "• 🖼 <b>Скриншоты и кадры</b>: Отправьте фото из фильма\n"
            "• 📝 <b>Поиск по сюжету</b>: Опишите сюжет фильма текстом\n\n"
            "🎲 <b>Команды:</b>\n"
            "• /random — Что посмотреть сегодня? (Лучшие фильмы по жанрам)\n"
            "• /lang — Сменить язык интерфейса\n"
            "• /about — О боте и контакты\n\n"
            "👨‍💻 <b>Связь и реклама:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>О боте AI FilmFinder</b>\n\n"
            "Этот бот — ваш персональный ИИ-гид для поиска кино по видеороликам, скриншотам и описанию сюжета! ✨\n\n"
            "🌟 <b>Возможности:</b>\n"
            "• 🎞 <b>Мгновенный поиск:</b> По Reels, Shorts, фото и тексту\n"
            "• 🎥 <b>Премьеры:</b> Информация о готовящихся к выходу фильмах\n"
            "• 🍿 <b>Трейлеры и просмотр:</b> Официальные трейлеры и онлайн-просмотр\n"
            "• 🎭 <b>Похожие фильмы:</b> Подборка кино по вашему вкусу\n"
            "• 🎲 <b>Случайный выбор:</b> Топ фильмов на вечер по жанрам\n\n"
            "📩 <b>Реклама и сотрудничество:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Администратор:</b> @khojayev_ramz\n\n"
            "❤️ <i>Делитесь ботом с друзьями!</i>"
        ),
        "status_downloading": "⏳ <b>Видео получено! Загрузка...</b>\n<i>(Это займет пару секунд)</i>",
        "status_analyzing": "🧠 <b>Искусственный интеллект анализирует видео...</b>\n<i>(Изучаются кадры, актеры, диалоги и сцена)</i>",
        "status_photo_search": "🧠 <b>Искусственный интеллект анализирует фото/скриншот...</b>\n<i>(Распознаются персонажи, сцена и детали)</i>",
        "status_plot_search": "🧠 <b>Искусственный интеллект ищет фильм по сюжету...</b>\n<i>(Поиск по глобальной базе кино)</i>",
        "status_similar_search": "🎭 <b>Подбираем похожие шедевры кино...</b>",
        "status_db": "🎬 <b>Поиск подробной информации...</b>",
        "error_download": (
            "❌ <b>Не удалось скачать видео!</b>\n\n"
            "• Проверьте правильность ссылки.\n"
            "• Убедитесь, что видео не находится в приватном профиле.\n"
            "• Или отправьте видео напрямую файлом."
        ),
        "error_not_found": (
            "😔 <b>К сожалению, фильм/сериал не удалось найти.</b>\n\n"
            "ℹ️ <b>Причина:</b> {reason}\n\n"
            "💡 <i>Совет: Попробуйте точнее описать сюжет или отправить более четкий кадр с главными героями.</i>"
        ),
        "error_general": "⚠️ <i>Извините, произошла непредвиденная ошибка. Попробуйте еще раз.</i>",
        "send_prompt": "Пожалуйста, отправьте ссылку на видео (Reels/Shorts), фото кадра или опишите сюжет фильма текстом! 🎬",
        "btn_trailer": "🎬 Официальный трейлер (YouTube)",
        "btn_trailer_search": "🎬 Искать трейлер",
        "btn_watch_uz": "🍿 Смотреть онлайн",
        "btn_similar": "🎭 Похожие фильмы",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Кинопоиск",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Поделиться с друзьями",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_contact_admin": "👨‍💻 Связаться с админом",
        "btn_random_more": "🔄 Другой фильм",
        "btn_back_genres": "🔙 Выбрать другой жанр",
        "random_choose_genre": "🎲 <b>Какой жанр фильма хотите посмотреть сегодня? Выберите:</b>",
        "genre_action": "💥 Боевик & Экшн",
        "genre_comedy": "😂 Комедия",
        "genre_scifi": "🚀 Фантастика & Космос",
        "genre_horror": "😱 Ужасы & Триллер",
        "genre_drama": "🎭 Драма & Жизненное",
        "genre_cartoon": "🎨 Мультфильм & Семейное",
        "genre_anime": "🌸 Аниме",
        "lang_changed": "✅ Язык успешно изменен на <b>Русский</b>!",
        "share_text": "Я нашел этот отличный фильм: {title} 🎬",
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
        "label_scene": "🔎 <b>Сцена:</b>",
        "label_summary": "📖 <b>Краткий сюжет:</b>",
        "label_why_watch": "💡 <b>Почему стоит посмотреть:</b>",
        "label_found_by": "🤖 <i>Найдено: AI Vision & Plot Engine</i>"
    },

    "en": {
        "choose_lang": "🌐 <b>Please choose your language / Iltimos, tilni tanlang / Выберите язык:</b>",
        "welcome": (
            "Hello, <b>{name}</b>! 👋\n\n"
            "🎬 Welcome to <b>AI Movie Finder Bot</b>!\n\n"
            "I can identify any <b>movie, TV series, anime, or cartoon</b> in 3 convenient ways: 🤖✨\n\n"
            "1️⃣ <b>By Video:</b> Send an Instagram Reels or YouTube Shorts link or upload a video.\n"
            "2️⃣ <b>By Screenshot:</b> Upload a photo or frame capture from a movie.\n"
            "3️⃣ <b>By Plot Description:</b> Forgot the name? Just describe what happens (e.g. <i>\"A man stranded on a desert island with a volleyball\"</i>).\n\n"
            "🎲 Wondering what to watch? Use /random!\n\n"
            "🚀 <i>Send a link, photo, or text description now!</i>"
        ),
        "help": (
            "💡 <b>Help & Guide:</b>\n\n"
            "🔍 <b>Search Methods:</b>\n"
            "• 📸 <b>Instagram Reels & YouTube Shorts</b> links\n"
            "• 📁 <b>Direct Videos</b> & video notes from Telegram\n"
            "• 🖼 <b>Screenshots & Photos</b>: Send any movie still\n"
            "• 📝 <b>Plot Search</b>: Describe the movie in your own words\n\n"
            "🎲 <b>Commands:</b>\n"
            "• /random — What to watch tonight? (Top movies by genre)\n"
            "• /lang — Change language\n"
            "• /about — About bot & contact\n\n"
            "👨‍💻 <b>Contact & Support:</b> @khojayev_ramz"
        ),
        "about": (
            "🎬 <b>About AI FilmFinder</b>\n\n"
            "This bot is your AI-powered companion for instantly discovering movies from video clips, photos, and plot memories! ✨\n\n"
            "🌟 <b>Key Features:</b>\n"
            "• 🎞 <b>Fast Search:</b> Video, Screenshot, and Text Plot recognition\n"
            "• 🎥 <b>Upcoming Premieres:</b> Discover unreleased movies and dates\n"
            "• 🍿 <b>Trailers & Streaming:</b> Watch trailers & find streaming links\n"
            "• 🎭 <b>Similar Movies:</b> AI-curated recommendations for any title\n"
            "• 🎲 <b>Random Pick:</b> Top-rated movie picks for movie night\n\n"
            "📩 <b>For ads and inquiries:</b> @khojayev_ramz\n"
            "👨‍💻 <b>Admin / Developer:</b> @khojayev_ramz\n\n"
            "❤️ <i>Share with your friends!</i>"
        ),
        "status_downloading": "⏳ <b>Video received! Downloading...</b>\n<i>(This takes a few seconds)</i>",
        "status_analyzing": "🧠 <b>AI is analyzing the video frames & audio...</b>\n<i>(Examining characters, actors, dialogue, and scene context)</i>",
        "status_photo_search": "🧠 <b>AI is analyzing the screenshot/photo...</b>\n<i>(Recognizing actors, setting, and costumes)</i>",
        "status_plot_search": "🧠 <b>AI is searching by storyline description...</b>\n<i>(Matching global movie databases)</i>",
        "status_similar_search": "🎭 <b>Curating top similar movie recommendations...</b>",
        "status_db": "🎬 <b>Fetching movie metadata...</b>",
        "error_download": (
            "❌ <b>Could not download video!</b>\n\n"
            "• Make sure the URL is valid.\n"
            "• Ensure the video is public.\n"
            "• Or upload the video file directly."
        ),
        "error_not_found": (
            "😔 <b>Sorry, could not find the movie.</b>\n\n"
            "ℹ️ <b>Reason:</b> {reason}\n\n"
            "💡 <i>Tip: Try providing more details about the plot or sending a clearer image with the actors.</i>"
        ),
        "error_general": "⚠️ <i>Sorry, an unexpected error occurred. Please try again.</i>",
        "send_prompt": "Please send a video link (Reels/Shorts), a screenshot photo, or describe the movie plot in text! 🎬",
        "btn_trailer": "🎬 Official Trailer (YouTube)",
        "btn_trailer_search": "🎬 Search Trailer",
        "btn_watch_uz": "🍿 Watch Online",
        "btn_similar": "🎭 Similar Movies",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Kinopoisk",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Share with Friends",
        "btn_change_lang": "🌐 Change Language",
        "btn_contact_admin": "👨‍💻 Contact Admin",
        "btn_random_more": "🔄 Another Recommendation",
        "btn_back_genres": "🔙 Select Another Genre",
        "random_choose_genre": "🎲 <b>What genre would you like to watch today? Choose below:</b>",
        "genre_action": "💥 Action & Adventure",
        "genre_comedy": "😂 Comedy",
        "genre_scifi": "🚀 Sci-Fi & Fantasy",
        "genre_horror": "😱 Horror & Thriller",
        "genre_drama": "🎭 Drama & Biography",
        "genre_cartoon": "🎨 Animation & Family",
        "genre_anime": "🌸 Anime",
        "lang_changed": "✅ Language changed to <b>English</b>!",
        "share_text": "I found this great movie: {title} 🎬",
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
        "label_scene": "🔎 <b>Scene:</b>",
        "label_summary": "📖 <b>Summary:</b>",
        "label_why_watch": "💡 <b>Why Watch:</b>",
        "label_found_by": "🤖 <i>Identified by: AI Vision & Plot Engine</i>"
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
