# 🎬 AI Movie Finder Telegram Bot

Instagram Reels, TikTok, YouTube Shorts havolalari yoki to'g'ridan-to'g'ri yuborilgan videolardan **qaysi kino, serial, anime yoki multfilm** ekanligini real vaqtda aniqlab beruvchi professional Telegram bot.

---

## 🌟 Asosiy Imkoniyatlari

- ⚡️ **Multimodal AI Vision & Audio**: Videoni tomosha qilib, aktyorlar, liboslar, yuzlar, saundtrek va sahnalar orqali film nomini aniqlaydi.
- 🔴 **Premyera va Kelgusi Filmlarni aniqlash**: Agar video hali chiqmagan film yoki serial treyleri bo'lsa, bot buni aniqlab, kutilayotgan premyera sanasini ko'rsatadi.
- 📸 **TMDb Integratsiyasi**: Filmning rasmiy HD posteri, IMDb/TMDb reytingi, aktyorlar ro'yxati, rasmiy janrlari va YouTube treyleri bilan chiroyli formatda taqdim etadi.
- 🔗 **Ko'p Platformali Qo'llab-quvvatlash**:
  - Instagram Reels va postlar
  - TikTok videolari
  - YouTube Shorts va videolari
  - Pinterest videolari
  - Telegram orqali yuborilgan video fayllar va video xabarlar (dumaloq video)
- 🚀 **Tezkor va Asinxron**: `aiogram 3.x` va `asyncio` asosida qurilgan.

---

## 🔑 Kerakli API Kalitlarni Olish

Bot ishlashi uchun 3 ta bepul kalit kerak bo'ladi:

1. **Telegram Bot Token**:
   - Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
   - `/newbot` buyrug'ini yuboring va nom bering.
   - Olingan `HTTP API Token`ni nusxalab oling.

2. **Google Gemini API Key**:
   - [Google AI Studio](https://aistudio.google.com/) saytiga kiring.
   - **Get API key** tugmasini bosib, bepul API kalit yarating va nusxalang.

3. **TMDb API Key** *(ixtiyoriy, lekin poster va reytinglar uchun tavsiya etiladi)*:
   - [themoviedb.org](https://www.themoviedb.org/) saytida ro'yxatdan o'ting.
   - `Settings -> API` bo'limidan bepul Developer API kalit oling.

---

## 🛠 O'rnatish va Ishga Tushirish

### 1. Virtual muhit yaratish va faollashtirish

Terminalda (PowerShell yoki CMD) loyiha papkasiga o'ting:

```powershell
cd C:\Users\Ramzbek\.gemini\antigravity\scratch\movie_finder_bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Kutubxonalarni o'rnatish

```powershell
pip install -r requirements.txt
```

### 3. `.env` faylini to'ldirish

Loyiha papkasidagi `.env` faylini oching va kalitlaringizni kiriting:

```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
GEMINI_API_KEY=AIzaSyD...
TMDB_API_KEY=your_tmdb_api_key
GEMINI_MODEL=gemini-2.0-flash
MAX_VIDEO_SIZE_MB=50
```

### 4. Botni ishga tushirish

```powershell
python run.py
```

---

## 📂 Loyiha Tuzilishi

```text
movie_finder_bot/
├── bot/
│   ├── handlers/
│   │   ├── start.py          # /start, /help, /about buyruqlari
│   │   └── analyze.py        # Havola va videolarni tahlil qilish handlerlari
│   ├── services/
│   │   ├── downloader.py     # yt-dlp orqali videolarni yuklab olish
│   │   ├── ai_service.py     # Gemini 2.0 orqali kinoni aniqlash
│   │   └── tmdb_service.py   # TMDb dan poster, reyting va premyera ma'lumotlari
│   ├── keyboards/
│   │   └── inline.py         # Treyler, Kinopoisk, IMDb va ulashish tugmalari
│   ├── config.py             # Sozlamalar va .env yuklovchi
│   └── utils.py              # Matn formatlash va yordamchi funksiyalar
├── downloads/                # Vaqtinchalik video fayllar papkasi
├── .env                      # API kalitlar fayli
├── .env.example              # Namuna sozlamalar
├── requirements.txt          # Python paketlar
├── run.py                    # Asosiy ishga tushirish skripti
└── README.md                 # To'liq qo'llanma
```

---

## 💡 Maslahatlar
- Bot foydalanuvchiga real vaqtda animatsion statuslar orqali qaysi jarayonda ekanligini ko'rsatib turadi (`⏳ Video yuklanmoqda...`, `🧠 AI tahlil qilmoqda...`).
- Yuklab olingan barcha vaqtinchalik videolar tahlil tugagach avtomatik o'chiriladi, diskda joy egallamaydi.
