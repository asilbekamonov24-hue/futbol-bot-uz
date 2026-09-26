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

# --- KOP TILLI TARJIMALAR ---
TRANSLATIONS = {
    "uz": {
        "welcome": "Salom, {name}! Futbol tahlil botiga xush kelibsiz. Kerakli bo'limni tanlang:",
        "daily_btn": "📊 Kunlik prognoz",
        "match_btn": "📅 Match-center (O'yinlar)",
        "ai_btn": "🤖 AI Tahlil & Koeffitsientlar",
        "help_btn": "ℹ️ Yordam",
        "settings_btn": "⚙️ Sozlamalar",
        "daily_text": "📊 **Bugungi kunlik prognoz:**\n\nReal Madrid vs Barcelona - O'yin shiddatli o'tishi va jamoalar gol almashishi kutilmoqda.",
        "match_wait": "⏳ Bugungi o'yinlar taqvimi va natijalari yuklanmoqda...",
        "match_title": "📅 **Bugungi Match-center (O'yinlar va Natijalar):**\n\n• Real Madrid 2:1 Barcelona (Tugadi)\n• Manchester City vs Arsenal (21:00)\n• Bayern Munich vs Dortmund (23:30)\n• Milan vs Inter (00:45)",
        "ai_wait": "⏳ Sun'iy intellekt tahlil qilmoqda...",
        "ai_title": "🤖 AI Real Vaqt Tahlili:",
        "error": "❌ Ma'lumot olishda xatolik yuz berdi.",
        "settings_menu": "⚙️ **Sozlamalar bo'limi:**\nBot tilini o'zgartirish uchun pastdagi tugmani bosing:",
        "lang_select": "🌐 Tilni tanlang:",
        "saved": "✅ Muvaffaqiyatli saqlandi!"
    },
    "ru": {
        "welcome": "Привет, {name}! Добро пожаловать в бот футбольной аналитики. Выберите раздел:",
        "daily_btn": "📊 Ежедневный прогноз",
        "match_btn": "📅 Матч-центр (Матчи)",
        "ai_btn": "🤖 ИИ Анализ & Коэффициенты",
        "help_btn": "ℹ️ Помощь",
        "settings_btn": "⚙️ Настройки",
        "daily_text": "📊 **Прогноз на сегодня:**\n\nРеал Мадрид против Барселоны - Ожидается яркая игра.",
        "match_wait": "⏳ Загрузка расписания и результатов матчей...",
        "match_title": "📅 **Матч-центр на сегодня:**\n\n• Реал Мадрид 2:1 Барселона (Завершено)\n• Манчестер Сити vs Арсенал (21:00)\n• Бавария vs Боруссия (23:30)",
        "ai_wait": "⏳ Искусственный интеллект анализирует...",
        "ai_title": "🤖 ИИ Анализ:",
        "error": "❌ Произошла ошибка.",
        "settings_menu": "⚙️ **Настройки:**\nВыберите язык:",
        "lang_select": "🌐 Выберите язык:",
        "saved": "✅ Успешно сохранено!"
    },
    "en": {
        "welcome": "Hello, {name}! Welcome to the Football Analytics Bot. Choose a section:",
        "daily_btn": "📊 Daily Forecast",
        "match_btn": "📅 Match Center",
        "ai_btn": "🤖 AI Analysis & Odds",
        "help_btn": "ℹ️ Help",
        "settings_btn": "⚙️ Settings",
        "daily_text": "📊 **Today's Forecast:**\n\nReal Madrid vs Barcelona - Intense match expected.",
        "match_wait": "⏳ Loading match schedule and results...",
        "match_title": "📅 **Today's Match Center:**\n\n• Real Madrid 2:1 Barcelona (Finished)\n• Manchester City vs Arsenal (21:00)\n• Bayern Munich vs Dortmund (23:30)",
        "ai_wait": "⏳ AI is analyzing...",
        "ai_title": "🤖 AI Analysis:",
        "error": "❌ An error occurred.",
        "settings_menu": "⚙️ **Settings:**\nSelect language:",
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
            [KeyboardButton(text=t["daily_btn"]), KeyboardButton(text=t["match_btn"])],
            [KeyboardButton(text=t["ai_btn"])],
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
        "uz": "🤖 Bot imkoniyatlari:\n• Kunlik bashoratlar\n• Match-center (O'yinlar va natijalar)\n• Real vaqtdagi AI tahlil\n• /stat - Foydalanuvchilar soni",
        "ru": "🤖 Возможности бота:\n• Ежедневные прогнозы\n• Матч-центр (Расписание и результаты)\n• ИИ анализ\n• /stat - Количество пользователей",
        "en": "🤖 Bot features:\n• Daily forecasts\n• Match center\n• AI analysis\n• /stat - User count"
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

# --- MATCH-CENTER ---
@dp.message(F.text.in_(["📅 Match-center (O'yinlar)", "📅 Матч-центр (Матчи)", "📅 Match Center"]))
async def match_center(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["match_title"], parse_mode="Markdown")

# --- AI ANALIZ ---
@dp.message(F.text.in_(["🤖 AI Tahlil & Koeffitsientlar", "🤖 ИИ Анализ & Коэффициенты", "🤖 AI Analysis & Odds"]))
async def ai_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["ai_wait"])
    
    prompt = "Bugungi eng muhim futbol o'yinlari bo'yicha tahlil yoz."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    await message.answer(f"{t['ai_title']}\n\n{ai_text}")
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
