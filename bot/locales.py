# Localization dictionaries for 4 languages: uz (Lotin), uz_kr (Кирилл), ru (Русский), en (English)

MESSAGES = {
    "uz": {
        "welcome": (
            "👋 Assalomu alaykum, <b>{name}</b>!\n\n"
            "🎬 <b>AI FilmFinder</b> botiga xush kelibsiz!\n"
            "Men Instagram Reels, YouTube Shorts, skrinshot, foto yoki matnli voqea tavsifidan filmlar, seriallar va multfilmlarni aniqlab beruvchi <b>Sun'iy Intellekt</b> yordamchingizman.\n\n"
            "✨ <b>Asosiy Imkoniyatlar:</b>\n"
            "1️⃣ <b>Video orqali:</b> Instagram Reels yoki YouTube Shorts havolasini yuboring.\n"
            "2️⃣ <b>Skrinshot orqali:</b> Kinodan olingan bitta rasm/foto yuboring.\n"
            "3️⃣ <b>Matn orqali:</b> Kino nomini eslay olmasangiz, esingizda qolgan voqeani yozing.\n"
            "4️⃣ <b>Kayfiyat orqali:</b> <i>\"Yomg'irli kunda ko'rishga yoqimli kino top\"</i> deb yozing.\n\n"
            "🎲 <b>/random</b> — AI orqali kayfiyatga mos kino tanlash!\n"
            "❤️ <b>/saved</b> — Saqlangan kinolar ro'yxatingiz (Watchlist)\n"
            "🎮 <b>/quiz</b> — Qiziqarli AI Kino Viktorinasi va ballar yig'ish!\n\n"
            "🚀 <i>Hoziroq birorta havola, rasm yoki matn yuborib sinab ko'ring!</i>"
        ),
        "choose_lang": "🌐 <b>Iltimos, muloqot tilini tanlang:</b>\n<i>Пожалуйста, выберите язык:</i>\n<i>Please choose your language:</i>",
        "lang_changed": "✅ Til muvaffaqiyatli o'zgartirildi!",
        "status_downloading": "⏳ <b>Video yuklab olinmoqda...</b>\n<i>(Iltimos, bir necha soniya kuting)</i>",
        "status_analyzing": "🧠 <b>Sun'iy intellekt kadrlarni tahlil qilmoqda...</b>\n<i>(Kino, serial yoki multfilm aniqlanmoqda)</i>",
        "status_photo_search": "🔍 <b>Rasm sun'iy intellekt orqali tahlil qilinmoqda...</b>",
        "status_plot_search": "🧠 <b>Syujet tavsifi bo'yicha film qidirilmoqda...</b>",
        "status_similar_search": "🍿 <b>Sun'iy intellekt o'xshash filmlarni tanlamoqda...</b>",
        "status_db": "🍿 <b>Kino ma'lumotlari bazadan yuklanmoqda...</b>",
        "error_download": (
            "❌ <b>Videoni yuklab bo'lmadi!</b>\n\n"
            "• Havola to'g'riligini tekshiring.\n"
            "• Video shaxsiy (private) yoki yopiq profilda emasligiga ishonch hosil qiling.\n"
            "• Yoki videoni to'g'ridan-to'g'ri fayl ko'rinishida yuboring."
        ),
        "error_not_found": (
            "😔 <b>Kino topilmadi!</b>\n\n"
            "<b>Sabab:</b> {reason}\n\n"
            "💡 <i>Maslahat: Videoni tiniqroq yoki boshqa sahnasini yuborib ko'ring yoki kino voqeasini matn ko'rinishida yozing.</i>"
        ),
        "error_general": "⚠️ <b>Kutilmagan xatolik yuz berdi.</b> Iltimos, keyinroq qayta urinib ko'ring.",
        "send_prompt": "🎬 Iltimos, video havolasi (Instagram/YouTube), rasm yoki kino syujetini yozib yuboring.",
        "label_type": "📌 <b>Turi:</b>",
        "label_year": "📅 <b>Yili:</b>",
        "label_premiere": "🔥 <b>Tez kunda / Premyera!</b>",
        "label_rating": "⭐️ <b>Reyting:</b>",
        "label_genres": "🎭 <b>Janr:</b>",
        "label_actors": "👥 <b>Qahramonlar/Aktyorlar:</b>",
        "label_scene": "🎬 <b>Sahna tavsifi:</b>",
        "label_summary": "📖 <b>Qisqacha mazmuni:</b>",
        "label_found_by": "🤖 <i>@FilmAiFinderbot orqali topildi</i>",
        "btn_trailer": "🎬 Rasmiy Treyler (YouTube)",
        "btn_trailer_search": "🎬 Treylerni qidirish",
        "btn_watch_uz": "🍿 O'zbek tilida ko'rish",
        "btn_similar": "🎭 Shunga o'xshash filmlar",
        "btn_save_movie": "❤️ Saqlab qo'yish",
        "btn_saved_done": "💖 Saqlangan",
        "btn_premiere_alert": "🔔 Chiqqanda xabar ber",
        "btn_alert_done": "🔕 Eslatma o'rnatildi",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Kinopoisk",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Do'stlarga ulashish",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_contact_admin": "👨‍💻 Dasturchi bilan bog'lanish",
        "btn_random_more": "🔄 Boshqa kino tavsiya qilish",
        "btn_back_genres": "🔙 Janrlar ro'yxati",
        "btn_surprise_me": "🔮 AI Meni hayratda qoldir! (Surprise Me)",
        "btn_check_sub": "✅ Obunani tekshirish",
        "btn_next_quiz": "🎮 Keyingi savol",
        "btn_leaderboard": "🏆 TOP O'yinchilar",
        "sub_required": (
            "📢 <b>Botdan to'liq foydalanish uchun quyidagi homiy kanalimizga a'zo bo'ling:</b>\n\n"
            "<i>A'zo bo'lgach, 'Obunani tekshirish' tugmasini bosing:</i>"
        ),
        "sub_success": "✅ <b>Obuna tasdiqlandi!</b> Botdan bemalol foydalanishingiz mumkin.",
        "sub_failed": "❌ <b>Siz hali barcha kanallarga a'zo bo'lmadingiz!</b> Iltimos, a'zo bo'lib qayta tekshiring.",
        "watchlist_title": "❤️ <b>SIZNING SAQLANGAN KINOLARINGIZ (Watchlist):</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "watchlist_empty": "📭 <b>Sizda hali saqlangan kinolar yo'q.</b>\nTopilgan kinolar ostidagi '❤️ Saqlab qo'yish' tugmasini bosib to'plam hosil qiling!",
        "alerts_title": "🔔 <b>SIZ KUTAYOTGAN PREMYERALAR:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "alerts_empty": "📭 <b>Hozircha premyera eslatmalari o'rnatilmagan.</b>",
        "quiz_welcome": (
            "🎮 <b>AI KINO VIKTORINASIGA XUSH KELIBSIZ!</b>\n\n"
            "Har bir to'g'ri javob uchun <b>+10 ball</b> beriladi. Qani, bilimlaringizni sinab ko'ramiz!\n\n"
            "⏳ <i>Savol tayyorlanmoqda...</i>"
        ),
        "quiz_correct": "🎉 <b>BARAKALLA, TO'G'RI JAVOB! (+10 Ball)</b>\n\n💡 <i>{explanation}</i>",
        "quiz_wrong": "❌ <b>Afsus, noto'g'ri javob!</b>\n\n✅ <b>To'g'ri javob:</b> {correct}\n💡 <i>{explanation}</i>",
        "genre_action": "💥 Jangari (Action)",
        "genre_comedy": "😂 Komediya",
        "genre_scifi": "🚀 Fantastika & Kosmos",
        "genre_horror": "😱 Dahshat & Qo'rqinchli",
        "genre_drama": "🎭 Drama & Hayotiy",
        "genre_cartoon": "🎨 Multfilm & Oila",
        "genre_anime": "🌸 Anime",
        "genre_thriller": "🕵️‍♂️ Triller & Detektiv",
        "genre_romance": "❤️ Romantika & Sevgi",
        "random_choose_genre": (
            "🎲 <b>AI Bugun nima ko'rishni tavsiya qilsin?</b>\n\n"
            "Quyidagi tugmalardan birini tanlang yoki to'g'ridan-to'g'ri kayfiyatingizni yozib yuboring:\n"
            "<i>(Masalan: \"Yomg'irli kunda ko'rishga yoqimli kino\" yoki \"Miyani portlatadigan kutilmagan film\")</i>"
        ),
        "help": (
            "💡 <b>Botdan qanday foydalaniladi?</b>\n\n"
            "1️⃣ <b>Video orqali:</b> Instagram yoki YouTube Shorts havolasini yuboring.\n"
            "2️⃣ <b>Skrinshot / Foto orqali:</b> Kinodan olingan bitta suratni yuboring.\n"
            "3️⃣ <b>Matn orqali:</b> Kino voqeasini yoki kayfiyatingizni yozing.\n"
            "4️⃣ <b>🎲 /random:</b> AI kayfiyat kuratori orqali kino tanlash.\n"
            "5️⃣ <b>❤️ /saved:</b> Saqlangan sevimli kinolaringiz.\n"
            "6️⃣ <b>🎮 /quiz:</b> AI kino viktorinasi o'yini.\n\n"
            "👨‍💻 <b>Savollar va takliflar uchun:</b> @khojayev_ramz"
        ),
        "about": (
            "ℹ️ <b>FilmFinder AI Bot haqida</b>\n\n"
            "Ushbu bot eng ilg'or <b>Google Gemini 3.5 Flash</b> sun'iy intellekti va <b>TMDb</b> kino bazasi integratsiyasi asosida ishlaydi.\n\n"
            "👨‍💻 <b>Muallif:</b> @khojayev_ramz\n"
            "🚀 <b>Versiya:</b> 3.5 Master AI Edition"
        ),
        "share_text": "🎬 Ushbu bot orqali istalgan video, skrinshot yoki syujet matnidan kinolarni bir zumda topishingiz mumkin: @FilmAiFinderbot",
        "type_movie": "Film (Kino)",
        "type_series": "Serial",
        "type_cartoon": "Multfilm",
        "type_anime": "Anime",
        "type_trailer": "Rasmiy Treyler"
    },
    "uz_kr": {
        "welcome": (
            "👋 Ассалому алайкум, <b>{name}</b>!\n\n"
            "🎬 <b>AI FilmFinder</b> ботига хуш келибсиз!\n"
            "🎲 <b>/random</b> — AI кино танлаш\n"
            "❤️ <b>/saved</b> — Сақланганлар\n"
            "🎮 <b>/quiz</b> — Кино викторинаси"
        ),
        "choose_lang": "🌐 <b>Илтимос, мулоқот тилини танланг:</b>",
        "lang_changed": "✅ Тил муваффақиятли ўзгартирилди!",
        "status_downloading": "⏳ <b>Видео юклаб олинмоқда...</b>",
        "status_analyzing": "🧠 <b>Сунъий интеллект кадрларни таҳлил қилмоқда...</b>",
        "status_photo_search": "🔍 <b>Расм сунъий интеллект орқали таҳлил қилинмоқда...</b>",
        "status_plot_search": "🧠 <b>Сюжет тавсифи бўйича фильм қидирилмоқда...</b>",
        "status_similar_search": "🍿 <b>Сунъий интеллект ўхшаш фильмларни танламоқда...</b>",
        "status_db": "🍿 <b>Кино маълумотлари базадан юкланмоқда...</b>",
        "error_download": "❌ <b>Видеони юклаб бўлмади!</b>",
        "error_not_found": "😔 <b>Кино топилмади!</b>\n\n<b>Сабаб:</b> {reason}",
        "error_general": "⚠️ <b>Кутилмаган хатолик юз берди.</b>",
        "send_prompt": "🎬 Илтимос, видео ҳаволаси, расм ёки кино сюжетини ёзиб юборинг.",
        "label_type": "📌 <b>Тури:</b>",
        "label_year": "📅 <b>Йили:</b>",
        "label_premiere": "🔥 <b>Тез кунда / Премьера!</b>",
        "label_rating": "⭐️ <b>Рейтинг:</b>",
        "label_genres": "🎭 <b>Жанр:</b>",
        "label_actors": "👥 <b>Қаҳрамонлар/Актёрлар:</b>",
        "label_scene": "🎬 <b>Саҳна тавсифи:</b>",
        "label_summary": "📖 <b>Қисқача мазмуни:</b>",
        "label_found_by": "🤖 <i>@FilmAiFinderbot орқали топилди</i>",
        "btn_trailer": "🎬 Расмий Трейлер (YouTube)",
        "btn_trailer_search": "🎬 Трейлерни қидириш",
        "btn_watch_uz": "🍿 Ўзбек тилида кўриш",
        "btn_similar": "🎭 Шунга ўхшаш фильмлар",
        "btn_save_movie": "❤️ Сақлаб қўйиш",
        "btn_saved_done": "💖 Сақланган",
        "btn_premiere_alert": "🔔 Чиққанда хабар бер",
        "btn_alert_done": "🔕 Эслатма ўрнатилди",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Кинопоиск",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Дўстларга улашиш",
        "btn_change_lang": "🌐 Тилни ўзгартириш",
        "btn_contact_admin": "👨‍💻 Дастурчи билан боғланиш",
        "btn_random_more": "🔄 Бошқа кино тавсия қилиш",
        "btn_back_genres": "🔙 Жанрлар рўйхати",
        "btn_surprise_me": "🔮 AI Мени ҳайратда қолдир! (Surprise Me)",
        "btn_check_sub": "✅ Обунани текшириш",
        "btn_next_quiz": "🎮 Кейинги савол",
        "btn_leaderboard": "🏆 ТОП Ўйинчилар",
        "sub_required": "📢 <b>Ботдан фойдаланиш учун каналга аъзо бўлинг:</b>",
        "sub_success": "✅ <b>Обуна тасдиқланди!</b>",
        "sub_failed": "❌ <b>Сиз ҳали аъзо бўлмадингиз!</b>",
        "watchlist_title": "❤️ <b>САҚЛАНГАН КИНОЛАРИНГИЗ:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "watchlist_empty": "📭 <b>Сақланган кинолар йўқ.</b>",
        "alerts_title": "🔔 <b>КУТИЛАЁТГАН ПРЕМЬЕРАЛАР:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "alerts_empty": "📭 <b>Премьера эслатмалари йўқ.</b>",
        "quiz_welcome": "🎮 <b>КИНО ВИКТОРИНАСИ!</b> (+10 балл)\n\n⏳ <i>Савол тайёрланмоқда...</i>",
        "quiz_correct": "🎉 <b>ТЎҒРИ ЖАВОБ! (+10 Балл)</b>\n\n💡 <i>{explanation}</i>",
        "quiz_wrong": "❌ <b>Нотўғри!</b>\n\n✅ <b>Тўғри жавоб:</b> {correct}\n💡 <i>{explanation}</i>",
        "genre_action": "💥 Жангари (Action)",
        "genre_comedy": "😂 Комедия",
        "genre_scifi": "🚀 Фантастика & Космос",
        "genre_horror": "😱 Даҳшат & Қўрқинчли",
        "genre_drama": "🎭 Драма & Ҳаётий",
        "genre_cartoon": "🎨 Мультфильм & Оила",
        "genre_anime": "🌸 Аниме",
        "genre_thriller": "🕵️‍♂️ Триллер & Детектив",
        "genre_romance": "❤️ Романтика & Севги",
        "random_choose_genre": "🎲 <b>AI Бугун нима кўришни тавсия қилсин?</b>",
        "help": "💡 <b>Ботдан қандай фойдаланилади?</b>\n👨‍💻 <b>Алоқа:</b> @khojayev_ramz",
        "about": "ℹ️ <b>FilmFinder AI Bot ҳақида</b>\n👨‍💻 <b>Муаллиф:</b> @khojayev_ramz",
        "share_text": "🎬 Кино ва сериалларни топувчи бот: @FilmAiFinderbot",
        "type_movie": "Фильм",
        "type_series": "Сериал",
        "type_cartoon": "Мультфильм",
        "type_anime": "Аниме",
        "type_trailer": "Расмий Трейлер"
    },
    "ru": {
        "welcome": (
            "👋 Здравствуйте, <b>{name}</b>!\n\n"
            "🎬 Добро пожаловать в <b>AI FilmFinder</b> бот!\n"
            "🎲 <b>/random</b> — AI Подбор фильмов\n"
            "❤️ <b>/saved</b> — Избранное (Watchlist)\n"
            "🎮 <b>/quiz</b> — Киновикторина с баллами"
        ),
        "choose_lang": "🌐 <b>Пожалуйста, выберите язык общения:</b>",
        "lang_changed": "✅ Язык успешно изменён!",
        "status_downloading": "⏳ <b>Скачивание видео...</b>",
        "status_analyzing": "🧠 <b>ИИ анализирует кадры...</b>",
        "status_photo_search": "🔍 <b>ИИ распознаёт изображение...</b>",
        "status_plot_search": "🧠 <b>Поиск фильма по сюжету...</b>",
        "status_similar_search": "🍿 <b>ИИ подбирает похожие фильмы...</b>",
        "status_db": "🍿 <b>Загрузка метаданных фильма...</b>",
        "error_download": "❌ <b>Не удалось скачать видео!</b> Проверьте ссылку.",
        "error_not_found": "😔 <b>Фильм не найден!</b>\n\n<b>Причина:</b> {reason}",
        "error_general": "⚠️ <b>Произошла непредвиденная ошибка.</b>",
        "send_prompt": "🎬 Пожалуйста, отправьте ссылку на видео, фото или описание сюжета.",
        "label_type": "📌 <b>Тип:</b>",
        "label_year": "📅 <b>Год:</b>",
        "label_premiere": "🔥 <b>Скоро / Премьера!</b>",
        "label_rating": "⭐️ <b>Рейтинг:</b>",
        "label_genres": "🎭 <b>Жанр:</b>",
        "label_actors": "👥 <b>В главных ролях:</b>",
        "label_scene": "🎬 <b>Описание сцены:</b>",
        "label_summary": "📖 <b>Сюжет:</b>",
        "label_found_by": "🤖 <i>Найдено через @FilmAiFinderbot</i>",
        "btn_trailer": "🎬 Официальный трейлер (YouTube)",
        "btn_trailer_search": "🎬 Найти трейлер",
        "btn_watch_uz": "🍿 Смотреть онлайн",
        "btn_similar": "🎭 Похожие фильмы",
        "btn_save_movie": "❤️ В избранное",
        "btn_saved_done": "💖 Сохранено",
        "btn_premiere_alert": "🔔 Напомнить о премьере",
        "btn_alert_done": "🔕 Напоминание включено",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Кинопоиск",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Поделиться",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_contact_admin": "👨‍💻 Связаться с автором",
        "btn_random_more": "🔄 Другой фильм",
        "btn_back_genres": "🔙 Выбор жанра",
        "btn_surprise_me": "🔮 AI Удиви меня! (Surprise Me)",
        "btn_check_sub": "✅ Проверить подписку",
        "btn_next_quiz": "🎮 Следующий вопрос",
        "btn_leaderboard": "🏆 ТОП Игроков",
        "sub_required": "📢 <b>Для использования бота подпишитесь на наш канал:</b>",
        "sub_success": "✅ <b>Подписка подтверждена!</b>",
        "sub_failed": "❌ <b>Вы еще не подписались на каналы!</b>",
        "watchlist_title": "❤️ <b>ВАШИ СОХРАНЕННЫЕ ФИЛЬМЫ:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "watchlist_empty": "📭 <b>У вас пока нет сохраненных фильмов.</b>",
        "alerts_title": "🔔 <b>ОЖИДАЕМЫЕ ПРЕМЬЕРЫ:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "alerts_empty": "📭 <b>Напоминаний нет.</b>",
        "quiz_welcome": "🎮 <b>КИНО-ВИКТОРИНА!</b> (+10 баллов)\n\n⏳ <i>Вопрос генерируется...</i>",
        "quiz_correct": "🎉 <b>ВЕРНО! (+10 Баллов)</b>\n\n💡 <i>{explanation}</i>",
        "quiz_wrong": "❌ <b>Неверно!</b>\n\n✅ <b>Правильный ответ:</b> {correct}\n💡 <i>{explanation}</i>",
        "genre_action": "💥 Боевик (Action)",
        "genre_comedy": "😂 Комедия",
        "genre_scifi": "🚀 Фантастика",
        "genre_horror": "😱 Ужасы & Хоррор",
        "genre_drama": "🎭 Драма",
        "genre_cartoon": "🎨 Мультфильм",
        "genre_anime": "🌸 Аниме",
        "genre_thriller": "🕵️‍♂️ Триллер & Детектив",
        "genre_romance": "❤️ Мелодрама & Романтика",
        "random_choose_genre": "🎲 <b>Что вам порекомендовать сегодня?</b>",
        "help": "💡 <b>Как пользоваться:</b>\nОтправьте ссылку на видео или фото.\n👨‍💻 <b>Связь:</b> @khojayev_ramz",
        "about": "ℹ️ <b>О боте FilmFinder AI</b>\n👨‍💻 <b>Автор:</b> @khojayev_ramz",
        "share_text": "🎬 Бот с ИИ для поиска фильмов: @FilmAiFinderbot",
        "type_movie": "Фильм",
        "type_series": "Сериал",
        "type_cartoon": "Мультфильм",
        "type_anime": "Аниме",
        "type_trailer": "Трейлер"
    },
    "en": {
        "welcome": (
            "👋 Hello, <b>{name}</b>!\n\n"
            "🎬 Welcome to <b>AI FilmFinder</b> bot!\n"
            "🎲 <b>/random</b> — AI Movie Curator\n"
            "❤️ <b>/saved</b> — Your Watchlist\n"
            "🎮 <b>/quiz</b> — AI Movie Quiz & Points"
        ),
        "choose_lang": "🌐 <b>Please choose your language:</b>",
        "lang_changed": "✅ Language successfully updated!",
        "status_downloading": "⏳ <b>Downloading video...</b>",
        "status_analyzing": "🧠 <b>AI is analyzing frames...</b>",
        "status_photo_search": "🔍 <b>AI is analyzing the image...</b>",
        "status_plot_search": "🧠 <b>Searching movie by plot...</b>",
        "status_similar_search": "🍿 <b>AI is curating similar movies...</b>",
        "status_db": "🍿 <b>Fetching movie metadata...</b>",
        "error_download": "❌ <b>Could not download video!</b> Please check the link.",
        "error_not_found": "😔 <b>Movie not found!</b>\n\n<b>Reason:</b> {reason}",
        "error_general": "⚠️ <b>An unexpected error occurred.</b>",
        "send_prompt": "🎬 Please send a video URL, image, or plot description.",
        "label_type": "📌 <b>Type:</b>",
        "label_year": "📅 <b>Year:</b>",
        "label_premiere": "🔥 <b>Upcoming / Premiere!</b>",
        "label_rating": "⭐️ <b>Rating:</b>",
        "label_genres": "🎭 <b>Genres:</b>",
        "label_actors": "👥 <b>Cast:</b>",
        "label_scene": "🎬 <b>Scene Context:</b>",
        "label_summary": "📖 <b>Plot Overview:</b>",
        "label_found_by": "🤖 <i>Found via @FilmAiFinderbot</i>",
        "btn_trailer": "🎬 Official Trailer (YouTube)",
        "btn_trailer_search": "🎬 Search Trailer",
        "btn_watch_uz": "🍿 Watch Online",
        "btn_similar": "🎭 Similar Movies",
        "btn_save_movie": "❤️ Save to Watchlist",
        "btn_saved_done": "💖 Saved",
        "btn_premiere_alert": "🔔 Remind on Premiere",
        "btn_alert_done": "🔕 Reminder set",
        "btn_imdb": "⭐️ IMDb",
        "btn_kinopoisk": "🍿 Kinopoisk",
        "btn_tmdb": "🌐 TMDb",
        "btn_google": "🔍 Google",
        "btn_share": "↗️ Share with friends",
        "btn_change_lang": "🌐 Change Language",
        "btn_contact_admin": "👨‍💻 Contact Developer",
        "btn_random_more": "🔄 Recommend Another Movie",
        "btn_back_genres": "🔙 Genres List",
        "btn_surprise_me": "🔮 AI Surprise Me!",
        "btn_check_sub": "✅ Check Subscription",
        "btn_next_quiz": "🎮 Next Question",
        "btn_leaderboard": "🏆 Top Players",
        "sub_required": "📢 <b>Please subscribe to our channel to continue:</b>",
        "sub_success": "✅ <b>Subscription verified!</b>",
        "sub_failed": "❌ <b>You are not subscribed yet!</b>",
        "watchlist_title": "❤️ <b>YOUR SAVED MOVIES (Watchlist):</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "watchlist_empty": "📭 <b>You have no saved movies yet.</b>",
        "alerts_title": "🔔 <b>UPCOMING PREMIERE REMINDERS:</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n",
        "alerts_empty": "📭 <b>No premiere alerts set.</b>",
        "quiz_welcome": "🎮 <b>AI MOVIE QUIZ!</b> (+10 points)\n\n⏳ <i>Generating question...</i>",
        "quiz_correct": "🎉 <b>CORRECT! (+10 Points)</b>\n\n💡 <i>{explanation}</i>",
        "quiz_wrong": "❌ <b>Wrong!</b>\n\n✅ <b>Correct answer:</b> {correct}\n💡 <i>{explanation}</i>",
        "genre_action": "💥 Action",
        "genre_comedy": "😂 Comedy",
        "genre_scifi": "🚀 Sci-Fi",
        "genre_horror": "😱 Horror",
        "genre_drama": "🎭 Drama",
        "genre_cartoon": "🎨 Cartoon & Animation",
        "genre_anime": "🌸 Anime",
        "genre_thriller": "🕵️‍♂️ Thriller & Mystery",
        "genre_romance": "❤️ Romance",
        "random_choose_genre": "🎲 <b>What would you like to watch today?</b>",
        "help": "💡 <b>How to use:</b>\nSend a video link, photo, or describe the plot.\n👨‍💻 <b>Contact:</b> @khojayev_ramz",
        "about": "ℹ️ <b>About FilmFinder AI</b>\n👨‍💻 <b>Author:</b> @khojayev_ramz",
        "share_text": "🎬 AI Movie Finder Bot: @FilmAiFinderbot",
        "type_movie": "Movie",
        "type_series": "TV Series",
        "type_cartoon": "Animation",
        "type_anime": "Anime",
        "type_trailer": "Official Trailer"
    }
}


def get_msg(lang: str, key: str, **kwargs) -> str:
    """Returns localized formatted string."""
    lang_dict = MESSAGES.get(lang, MESSAGES["uz"])
    msg = lang_dict.get(key, MESSAGES["uz"].get(key, f"[{key}]"))
    if kwargs:
        try:
            return msg.format(**kwargs)
        except Exception:
            return msg
    return msg
