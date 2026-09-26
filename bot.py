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
user_settings = {}  # {user_id: {"lang": "uz/ru/en", "score": 0}}

# --- KOP TILLI TARJIMALAR (SNG UCHUN) ---
TRANSLATIONS = {
    "uz": {
        "welcome": "Salom, {name}! Futbol tahlil botiga xush kelibsiz. Quyidagi menyudan foydalaning:",
        "daily_btn": "📊 Kunlik prognoz",
        "ai_btn": "🤖 AI Tahlil & Foizlar",
        "standings_btn": "🏆 Turnir jadvali",
        "quiz_btn": "⚽ Viktorina",
        "help_btn": "ℹ️ Yordam",
        "settings_btn": "⚙️ Sozlamalar",
        "daily_text": "📊 **Bugungi kunlik prognoz:**\n\nReal Madrid vs Barcelona - O'yin shiddatli o'tishi va jamoalar gol almashishi kutilmoqda.",
        "ai_wait": "⏳ Sun'iy intellekt o'yinlarni tahlil qilib, g'alaba qozonish ehtimolligi foizlarini hisoblamoqda...",
        "ai_title": "🤖 **AI Match Simulyatsiyasi va G'alaba Foizlari:**",
        "standings_text": "🏆 **Top Ligalar Turnir Jadvali (Joriy mavsum):**\n\n1. Real Madrid — 78 ochko\n2. Barcelona — 75 ochko\n3. Atletico — 68 ochko\n4. Girona — 62 ochko",
        "quiz_start": "⚽ **Futbol Viktorinasi!**\nSavol: Jahon chempionatini eng ko'p marta yutgan terma jamoa qaysi?",
        "error": "❌ Ma'lumot olishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
        "settings_menu": "⚙️ **Sozlamalar bo'limi:**\nBot tilini o'zgartirish uchun pastdagi tugmani bosing:",
        "lang_select": "🌐 Tilni tanlang:",
        "saved": "✅ Muvaffaqiyatli saqlandi!"
    },
    "ru": {
        "welcome": "Привет, {name}! Добро пожаловать в бот футбольной аналитики. Используйте меню ниже:",
        "daily_btn": "📊 Ежедневный прогноз",
        "ai_btn": "🤖 ИИ Анализ & Проценты",
        "standings_btn": "🏆 Турнирная таблица",
        "quiz_btn": "⚽ Викторина",
        "help_btn": "ℹ️ Помощь",
        "settings_btn": "⚙️ Настройки",
        "daily_text": "📊 **Прогноз на сегодня:**\n\nРеал Мадрид против Барселоны - Ожидается яркая игра и голы от обеих команд.",
        "ai_wait": "⏳ Искусственный интеллект анализирует матчи и рассчитывает проценты на победу...",
        "ai_title": "🤖 **ИИ Симуляция матчей и Шансы на победу:**",
        "standings_text": "🏆 **Турнирная таблица Топ-лиг:**\n\n1. Реал Мадрид — 78 очков\n2. Барселона — 75 очков\n3. Атлетико — 68 очков\n4. Жирона — 62 очка",
        "quiz_start": "⚽ **Футбольная викторина!**\nВопрос: какая сборная выигрывала Чемпионат мира больше всего раз?",
        "error": "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
        "settings_menu": "⚙️ **Меню настроек:**\nНажмите кнопку ниже, чтобы изменить язык бота:",
        "lang_select": "🌐 Выберите язык:",
        "saved": "✅ Успешно сохранено!"
    },
    "en": {
        "welcome": "Hello, {name}! Welcome to the Football Analytics Bot. Use the menu below:",
        "daily_btn": "📊 Daily Forecast",
        "ai_btn": "🤖 AI Analysis & Odds",
        "standings_btn": "🏆 Standings",
        "quiz_btn": "⚽ Quiz",
        "help_btn": "ℹ️ Help",
        "settings_btn": "⚙️ Settings",
        "daily_text": "📊 **Today's Forecast:**\n\nReal Madrid vs Barcelona - An intense match with goals from both sides is expected.",
        "ai_wait": "⏳ Artificial intelligence is analyzing matches and calculating win probabilities...",
        "ai_title": "🤖 **AI Match Simulation & Win Probabilities:**",
        "standings_text": "🏆 **Top Leagues Standings:**\n\n1. Real Madrid — 78 pts\n2. Barcelona — 75 pts\n3. Atletico — 68 pts\n4. Girona — 62 pts",
        "quiz_start": "⚽ **Football Quiz!**\nQuestion: Which national team has won the World Cup the most times?",
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
            [KeyboardButton(text=t["standings_btn"]), KeyboardButton(text=t["quiz_btn"])],
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

def get_quiz_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Braziliya / Бразилия / Brazil", callback_data="quiz_correct")],
            [InlineKeyboardButton(text="Br Germaniya / Германия / Germany", callback_data="quiz_wrong")]
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
        "uz": "🤖 **Bot imkoniyatlari:**\n• Kunlik bashoratlar\n• AI orqali g'alaba foizlari va simulyatsiya\n• Turnir jadvallari\n• Futbol viktorinasi\n• /stat - Foydalanuvchilar soni",
        "ru": "🤖 **Возможности бота:**\n• Ежедневные прогнозы\n• ИИ симуляция и проценты на победу\n• Турнирные таблицы\n• Футбольная викторина\n• /stat - Количество пользователей",
        "en": "🤖 **Bot features:**\n• Daily forecasts\n• AI match simulation & odds\n• Standings\n• Football quiz\n• /stat - User count"
    }
    await message.answer(texts.get(lang, texts["uz"]), parse_mode="Markdown")

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

# --- INLINE CALLBACKS (LANG & QUIZ) ---
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

@dp.callback_query(F.data == "quiz_correct")
async def cb_quiz_correct(callback: types.CallbackQuery):
    await callback.answer("To'g'ri! / Правильно! / Correct!", show_alert=True)
    await callback.message.answer("🎉 Tabriklayman, javobingiz to'g'ri! Braziliya 5 marta JCh g'olibi bo'lgan.")

@dp.callback_query(F.data == "quiz_wrong")
async def cb_quiz_wrong(callback: types.CallbackQuery):
    await callback.answer("Noto'g'ri / Неправильно / Wrong", show_alert=True)
    await callback.message.answer("❌ Afsuski noto'g'ri. To'g'ri javob: Braziliya.")

# --- KUNLIK PROGNOZ ---
@dp.message(F.text.in_(["📊 Kunlik prognoz", "📊 Ежедневный прогноз", "📊 Daily Forecast"]))
async def daily_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["daily_text"], parse_mode="Markdown")

# --- TURNIR JADVALI ---
@dp.message(F.text.in_(["🏆 Turnir jadvali", "🏆 Турнирная таблица", "🏆 Standings"]))
async def standings_handler(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["standings_text"], parse_mode="Markdown")

# --- VIKTORINA ---
@dp.message(F.text.in_(["⚽ Viktorina", "⚽ Викторина", "⚽ Quiz"]))
async def quiz_handler(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["quiz_start"], reply_markup=get_quiz_inline(), parse_mode="Markdown")

# --- AI ANALIZ & FOIZLAR (GEMINI) ---
@dp.message(F.text.in_(["🤖 AI Tahlil & Foizlar", "🤖 ИИ Анализ & Проценты", "🤖 AI Analysis & Odds"]))
async def ai_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    
    await message.answer(t["ai_wait"])
    
    prompts = {
        "uz": "Bugungi kundagi eng muhim top-5 futbol o'yini uchun professional tahlil va har bir o'yin uchun g'alaba qozonish ehtimolligi foizlarini (masalan: Real 60% - 20% Barca, Durang 20%) aniq yoz. O'zbek tilida.",
        "ru": "Напиши профессиональный анализ на топ-5 футбольных матчей на сегодня и укажи проценты вероятности победы команд (например: Реал 60% - 20% Барса, Ничья 20%). На русском языке.",
        "en": "Write a professional analysis for the top 5 football matches today and include win probabilities in percentages. In English."
    }
    prompt = prompts.get(lang, prompts["uz"])
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    if len(ai_text) > 4000:
                        ai_text = ai_text[:4000]
                    await message.answer(f"{t['ai_title']}\n\n{ai_text}", parse_mode="Markdown")
                else:
                    await message.answer(t["error"])
    except Exception:
        await message.answer(t["error"])

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
