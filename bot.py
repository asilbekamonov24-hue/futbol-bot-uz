import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# --- SOZLAMALAR ---
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bazalar
users_db = set()
user_settings = {}  # {user_id: {"lang": "uz/ru/en"}}

# --- KOP TILLI TARJIMALAR (SNG UCHUN) ---
TRANSLATIONS = {
    "uz": {
        "welcome": "Salom, {name}! Futbol tahlil botiga xush kelibsiz. Real vaqtdagi tahlillar uchun pastdagi tugmani bosing:",
        "daily_btn": "📊 Kunlik prognoz",
        "ai_btn": "🤖 AI Tahlil & Koeffitsientlar",
        "help_btn": "ℹ️ Yordam",
        "settings_btn": "⚙️ Sozlamalar",
        "daily_text": "📊 **Bugungi kunlik prognoz:**\n\nReal Madrid vs Barcelona - O'yin shiddatli o'tishi va jamoalar gol almashishi kutilmoqda.",
        "ai_wait": "⏳ Sun'iy intellekt bugungi real vaqtdagi o'yinlarni tahlil qilib, foizlar va koeffitsientlarni hisoblamoqda...",
        "ai_title": "🤖 AI Real Vaqt Tahlili, Foizlar va Koeffitsientlar:",
        "error": "❌ Ma'lumot olishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
        "settings_menu": "⚙️ **Sozlamalar bo'limi:**\nBot tilini o'zgartirish uchun pastdagi tugmani bosing:",
        "lang_select": "🌐 Tilni tanlang:",
        "saved": "✅ Muvaffaqiyatli saqlandi!"
    },
    "ru": {
        "welcome": "Привет, {name}! Добро пожаловать в бот футбольной аналитики. Нажмите кнопку ниже для анализа в реальном времени:",
        "daily_btn": "📊 Ежедневный прогноз",
        "ai_btn": "🤖 ИИ Анализ & Коэффициенты",
        "help_btn": "ℹ️ Помощь",
        "settings_btn": "⚙️ Настройки",
        "daily_text": "📊 **Прогноз на сегодня:**\n\nРеал Мадрид против Барселоны - Ожидается яркая игра и голы от обеих команд.",
        "ai_wait": "⏳ Искусственный интеллект анализирует сегодняшние матчи в реальном времени, рассчитывает проценты и коэффициенты...",
        "ai_title": "🤖 ИИ Анализ в реальном времени, Проценты и Коэффициенты:",
        "error": "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
        "settings_menu": "⚙️ **Меню настроек:**\nНажмите кнопку ниже, чтобы изменить язык бота:",
        "lang_select": "🌐 Выберите язык:",
        "saved": "✅ Успешно сохранено!"
    },
    "en": {
        "welcome": "Hello, {name}! Welcome to the Football Analytics Bot. Click the button below for real-time analysis:",
        "daily_btn": "📊 Daily Forecast",
        "ai_btn": "🤖 AI Analysis & Odds",
        "help_btn": "ℹ️ Help",
        "settings_btn": "⚙️ Settings",
        "daily_text": "📊 **Today's Forecast:**\n\nReal Madrid vs Barcelona - An intense match with goals from both sides is expected.",
        "ai_wait": "⏳ Artificial intelligence is analyzing today's live matches and calculating odds and probabilities...",
        "ai_title": "🤖 AI Real-Time Analysis, Probabilities & Odds:",
        "error": "❌ An error occurred. Please try again later.",
        "settings_menu": "⚙️ **Settings Menu:**\nClick the button below to change the bot language:",
        "lang_select": "🌐 Select language:",
        "saved": "✅ Successfully saved!"
    }
}

def get_user_lang(user_id):
    if user_id in user_settings and "lang" in user_settings[user_id]:
        return user_settings[user_id]["lang"]
    return "uz"

# --- KLAVIATURALAR ---
def get_main_keyboard(lang="uz"):
    t = TRANSLATIONS.get(lang, TRANSLATIONS["uz"])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["daily_btn"]), KeyboardButton(text=t["ai_btn"])],
            [KeyboardButton(text=t["help_btn"]), KeyboardButton(text=t["settings_btn"])]
        ],
        resize_keyboard=True
    )

def get_settings_inline(lang="uz"):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Tilni o'zgartirish / Сменить язык / Change Language", callback_data="set_lang")]
        ]
    )

def get_langs_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
             InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
        ]
    )

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    users_db.add(user_id)
    if user_id not in user_settings:
        user_settings[user_id] = {"lang": "uz"}
        
    lang = get_user_lang(user_id)
    t = TRANSLATIONS[lang]
    await message.answer(t["welcome"].format(name=message.from_user.first_name), reply_markup=get_main_keyboard(lang))

# --- HELP ---
@dp.message(Command("help"))
@dp.message(F.text.in_(["ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help"]))
async def cmd_help(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    texts = {
        "uz": "🤖 Bot imkoniyatlari:\n• Kunlik bashoratlar\n• Real vaqtdagi AI tahlil, g'alaba foizlari va koeffitsientlar\n• /stat - Foydalanuvchilar soni",
        "ru": "🤖 Возможности бота:\n• Ежедневные прогнозы\n• ИИ анализ в реальном времени, проценты и коэффициенты\n• /stat - Количество пользователей",
        "en": "🤖 Bot features:\n• Daily forecasts\n• Real-time AI analysis, win probabilities & odds\n• /stat - User count"
    }
    await message.answer(texts.get(lang, texts["uz"]))

# --- STAT ---
@dp.message(Command("stat"))
async def cmd_stat(message: types.Message):
    await message.answer(f"📊 Jami foydalanuvchilar (Total users): {len(users_db)} ta")

# --- SETTINGS ---
@dp.message(Command("settings"))
@dp.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки", "⚙️ Settings"]))
async def cmd_settings(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["settings_menu"], reply_markup=get_settings_inline(lang), parse_mode="HTML")

# --- INLINE CALLBACKS (LANG) ---
@dp.callback_query(F.data == "set_lang")
async def cb_set_lang(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TRANSLATIONS[lang]
    await callback.message.edit_text(t["lang_select"], reply_markup=get_langs_inline())

@dp.callback_query(F.data.startswith("lang_"))
async def cb_save_lang(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    new_lang = callback.data.split("_")[1]
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id]["lang"] = new_lang
    t = TRANSLATIONS[new_lang]
    await callback.answer(t["saved"])
    await callback.message.answer(t["welcome"].format(name=callback.from_user.first_name), reply_markup=get_main_keyboard(new_lang))

# --- KUNLIK PROGNOZ ---
@dp.message(F.text.in_(["📊 Kunlik prognoz", "📊 Ежедневный прогноз", "📊 Daily Forecast"]))
async def daily_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["daily_text"])

# --- AI ANALIZ, FOIZLAR VA KOEFFITSIENTLAR (KUCHAYtirilgan XAVFSIZ VERSIYA) ---
@dp.message(F.text.in_(["🤖 AI Tahlil & Koeffitsientlar", "🤖 ИИ Анализ & Коэффициенты", "🤖 AI Analysis & Odds"]))
async def ai_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    
    await message.answer(t["ai_wait"])
    
    prompts = {
        "uz": (
            "Bugungi kundagi eng muhim real vaqt rejimidagi futbol o'yinlari uchun professional tahlil tayyorla. "
            "Kamida 5 ta o'yinni tanlab, har biri uchun quyidagilarni aniq yoz:\n"
            "1. Jamoalar nomi\n"
            "2. G'alaba qozonish ehtimolligi foizlari\n"
            "3. Taxminiy bukmekerlik koeffitsientlari (Odds)\n"
            "4. Qisqacha ekspert tahlili.\n"
            "Javobni oddiy matn shaklida O'zbek tilida taqdim et."
        ),
        "ru": (
            "Подготовь профессиональный анализ в реальном времени на самые важные футбольные матчи на сегодня. "
            "Выбери как минимум 5 матчей и для каждого укажи:\n"
            "1. Названия команд\n"
            "2. Проценты вероятности победы\n"
            "3. Примерные букмекерские коэффициенты (Odds)\n"
            "4. Краткий экспертный анализ.\n"
            "Ответ предоставь в обычном текстовом формате на русском языке."
        ),
        "en": (
            "Prepare a professional real-time analysis for the most important football matches today. "
            "Select at least 5 matches and for each include:\n"
            "1. Team names\n"
            "2. Win probability percentages\n"
            "3. Estimated bookmaker odds (Odds)\n"
            "4. Brief expert analysis.\n"
            "Provide the response in a plain text format in English."
        )
    }
    prompt = prompts.get(lang, prompts["uz"])
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    if not GEMINI_API_KEY:
        await message.answer("❌ Xatolik: GEMINI_API_KEY Render'da kiritilmagan!")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    try:
                        ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError) as ke:
                        ai_text = f"AI javobida ma'lumot topilmadi. Tafsilot: {str(ke)}"
                    
                    if len(ai_text) > 4000:
                        ai_text = ai_text[:4000]
                    await message.answer(f"{t['ai_title']}\n\n{ai_text}")
                else:
                    err_body = await response.text()
                    print(f"API Error: {err_body}")
                    await message.answer(f"❌ API xatosi ({response.status}): {err_body[:150]}")
    except Exception as e:
        print(f"Exception error: {e}")
        await message.answer(f"❌ Tizim xatosi: {str(e)}")

# --- RENDER WEB SERVER ---
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    asyncio.create_task(web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
