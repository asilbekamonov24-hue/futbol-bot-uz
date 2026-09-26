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
        "welcome": "Salom, {name}! Futbol tahlil botiga xush kelibsiz. Quyidagi menyudan foydalaning:",
        "daily_btn": "📊 Kunlik prognoz",
        "ai_btn": "🤖 AI Tahlil & Foizlar",
        "help_btn": "ℹ️ Yordam",
        "settings_btn": "⚙️ Sozlamalar",
        "daily_text": "📊 **Bugungi kunlik prognoz:**\n\nReal Madrid vs Barcelona - O'yin shiddatli o'tishi va jamoalar gol almashishi kutilmoqda.",
        "ai_wait": "⏳ Sun'iy intellekt real vaqtdagi o'yinlarni tahlil qilib, g'alaba qozonish ehtimolligi foizlarini hisoblamoqda...",
        "ai_title": "🤖 **AI Real Vaqt Tahlili va G'alaba Foizlari:**",
        "error": "❌ Ma'lumot olishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
        "settings_menu": "⚙️ **Sozlamalar bo'limi:**\nBot tilini o'zgartirish uchun pastdagi tugmani bosing:",
        "lang_select": "🌐 Tilni tanlang:",
        "saved": "✅ Muvaffaqiyatli saqlandi!"
    },
    "ru": {
        "welcome": "Привет, {name}! Добро пожаловать в бот футбольной аналитики. Используйте меню ниже:",
        "daily_btn": "📊 Ежедневный прогноз",
        "ai_btn": "🤖 ИИ Анализ & Проценты",
        "help_btn": "ℹ️ Помощь",
        "settings_btn": "⚙️ Настройки",
        "daily_text": "📊 **Прогноз на сегодня:**\n\nРеал Мадрид против Барселоны - Ожидается яркая игра и голы от обеих команд.",
        "ai_wait": "⏳ Искусственный интеллект анализирует матчи в реальном времени и рассчитывает проценты...",
        "ai_title": "🤖 **ИИ Анализ в реальном времени и Шансы на победу:**",
        "error": "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
        "settings_menu": "⚙️ **Меню настроек:**\nНажмите кнопку ниже, чтобы изменить язык бота:",
        "lang_select": "🌐 Выберите язык:",
        "saved": "✅ Успешно сохранено!"
    },
    "en": {
        "welcome": "Hello, {name}! Welcome to the Football Analytics Bot. Use the menu below:",
        "daily_btn": "📊 Daily Forecast",
        "ai_btn": "🤖 AI Analysis & Odds",
        "help_btn": "ℹ️ Help",
        "settings_btn": "⚙️ Settings",
        "daily_text": "📊 **Today's Forecast:**\n\nReal Madrid vs Barcelona - An intense match with goals from both sides is expected.",
        "ai_wait": "⏳ Artificial intelligence is analyzing live matches and calculating win probabilities...",
        "ai_title": "🤖 **AI Real-Time Analysis & Win Probabilities:**",
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
        "uz": "🤖 **Bot imkoniyatlari:**\n• Kunlik bashoratlar\n• AI orqali real vaqtdagi g'alaba foizlari va tahlil\n• /stat - Foydalanuvchilar soni",
        "ru": "🤖 **Возможности бота:**\n• Ежедневные прогнозы\n• ИИ анализ матчей в реальном времени и проценты на победу\n• /stat - Количество пользователей",
        "en": "🤖 **Bot features:**\n• Daily forecasts\n• AI real-time match analysis & odds\n• /stat - User count"
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
    await message.answer(t["daily_text"], parse_mode="Markdown")

# --- AI ANALIZ & FOIZLAR (REAL VAQT REJIMIDA GEMINI ORQALI) ---
@dp.message(F.text.in_(["🤖 AI Tahlil & Foizlar", "🤖 ИИ Анализ & Проценты", "🤖 AI Analysis & Odds"]))
async def ai_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    
    await message.answer(t["ai_wait"])
    
    # Sun'iy intellektga real vaqt talabiga mos professional prompt beramiz
    prompts = {
        "uz": "Hozirgi kundagi eng muhim futbol o'yinlari uchun professional tahlil tayyorla. Har bir o'yin uchun jamoalar imkoniyatlarini va g'alaba qozonish ehtimolligi foizlarini (masalan: Real 55% - 25% Barca, Durang 20%) aniq ko'rsatib ber. O'zbek tilida.",
        "ru": "Подготовь профессиональный анализ на самые важные футбольные матчи на текущий момент. Для каждого матча укажи шансы команд и проценты вероятности победы (например: Реал 55% - 25% Барса, Ничья 20%). На русском языке.",
        "en": "Prepare a professional analysis for the most important football matches currently. For each match, clearly indicate team odds and win probability percentages (e.g., Real 55% - 25% Barca, Draw 20%). In English."
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
