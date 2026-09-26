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

# Foydalanuvchilar bazasi va ularning sozlamalari
users_db = set()
user_settings = {}  # {user_id: {"lang": "uz/ru/en", "team": "Real Madrid"}}

# --- MATNLAR (TARJIMALAR) ---
TRANSLATIONS = {
    "uz": {
        "welcome": "Salom, {name}! Futbol prognoz botiga xush kelibsiz. Quyidagi tugmalardan birini tanlang:",
        "daily_btn": "📊 Kunlik prognoz",
        "ai_btn": "🤖 AI Prognoz",
        "help_btn": "ℹ️ Yordam",
        "settings_btn": "⚙️ Sozlamalar",
        "daily_text": "📊 **Bugungi kunlik prognoz:**\n\nReal vs Barcelona - Bugun barca g'alaba qozonishi kutilmoqda",
        "ai_wait": "⏳ Sun'iy intellekt bugungi eng yaxshi 5 ta futbol o'yinini tahlil qilmoqda, biroz kuting...",
        "ai_title": "🤖 **Sun'iy Intellekt Tahlili (Top 5 O'yin):**",
        "error": "❌ AI tahlilini olishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
        "settings_menu": "⚙️ **Sozlamalar bo'limi:**\nTilni o'zgartiring yoki sevimli jamoangizni tanlang:",
        "team_select": "⚽ Sevimli jamoangizni tanlang:",
        "lang_select": "🌐 Tilni tanlang:",
        "saved": "✅ Muvaffaqiyatli saqlandi!"
    },
    "ru": {
        "welcome": "Привет, {name}! Добро пожаловать в бота футбольных прогнозов. Выберите нужную кнопку:",
        "daily_btn": "📊 Ежедневный прогноз",
        "ai_btn": "🤖 ИИ Прогноз",
        "help_btn": "ℹ️ Помощь",
        "settings_btn": "⚙️ Настройки",
        "daily_text": "📊 **Ежедневный прогноз на сегодня:**\n\nРеал против Барселоны - Ожидается победа Барсы",
        "ai_wait": "⏳ Искусственный интеллект анализирует топ-5 матчей на сегодня, подождите...",
        "ai_title": "🤖 **Анализ ИИ (Топ 5 матчей):**",
        "error": "❌ Произошла ошибка при получении анализа. Попробуйте позже.",
        "settings_menu": "⚙️ **Меню настроек:**\nИзмените язык или выберите любимую команду:",
        "team_select": "⚽ Выберите вашу любимую команду:",
        "lang_select": "🌐 Выберите язык:",
        "saved": "✅ Успешно сохранено!"
    },
    "en": {
        "welcome": "Hello, {name}! Welcome to the Football Forecast Bot. Choose an option below:",
        "daily_btn": "📊 Daily Forecast",
        "ai_btn": "🤖 AI Forecast",
        "help_btn": "ℹ️ Help",
        "settings_btn": "⚙️ Settings",
        "daily_text": "📊 **Today's Daily Forecast:**\n\nReal vs Barcelona - Barca is expected to win today",
        "ai_wait": "⏳ Artificial intelligence is analyzing the top 5 matches for today, please wait...",
        "ai_title": "🤖 **AI Analysis (Top 5 Matches):**",
        "error": "❌ An error occurred while getting the analysis. Please try again later.",
        "settings_menu": "⚙️ **Settings Menu:**\nChange your language or select your favorite team:",
        "team_select": "⚽ Select your favorite team:",
        "lang_select": "🌐 Select language:",
        "saved": "✅ Successfully saved!"
    }
}

def get_user_lang(user_id):
    if user_id in user_settings and "lang" in user_settings[user_id]:
        return user_settings[user_id]["lang"]
    return "uz"  # Standart til

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
            [InlineKeyboardButton(text="⚽ Sevimli jamoani tanlash", callback_data="set_team")],
            [InlineKeyboardButton(text="🌐 Tilni o'zgartirish (Change language)", callback_data="set_lang")]
        ]
    )

def get_teams_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Real Madrid", callback_data="team_Real Madrid"),
             InlineKeyboardButton(text="Barcelona", callback_data="team_Barcelona")],
            [InlineKeyboardButton(text="Manchester United", callback_data="team_Manchester United"),
             InlineKeyboardButton(text="Arsenal", callback_data="team_Arsenal")],
            [InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_settings")]
        ]
    )

def get_langs_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
             InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_settings")]
        ]
    )

# --- START BUYRUG'I ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    users_db.add(user_id)
    
    if user_id not in user_settings:
        user_settings[user_id] = {"lang": "uz", "team": "Tanlanmagan"}
        
    lang = get_user_lang(user_id)
    t = TRANSLATIONS[lang]
    
    text = t["welcome"].format(name=message.from_user.first_name)
    await message.answer(text, reply_markup=get_main_keyboard(lang))

# --- HELP ---
@dp.message(Command("help"))
@dp.message(F.text.in_(["ℹ️ Yordam", "ℹ️ Помощь", "ℹ️ Help"]))
async def cmd_help(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    if lang == "ru":
        text = "🤖 **Справка:**\nИспользуйте кнопки меню для прогнозов, а в /settings меняйте язык и команду."
    elif lang == "en":
        text = "🤖 **Help:**\nUse the menu buttons for forecasts, and /settings to change language and team."
    else:
        text = "🤖 **Yordam:**\nPrognozlar uchun menyu tugmalaridan foydalaning, /settings orqali til va jamoani o'zgartiring."
    await message.answer(text, parse_mode="Markdown")

# --- STAT ---
@dp.message(Command("stat"))
async def cmd_stat(message: types.Message):
    await message.answer(f"📊 Jami foydalanuvchilar: {len(users_db)} ta")

# --- SETTINGS ---
@dp.message(Command("settings"))
@dp.message(F.text.in_(["⚙️ Sozlamalar", "⚙️ Настройки", "⚙️ Settings"]))
async def cmd_settings(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    team = user_settings.get(message.from_user.id, {}).get("team", "Tanlanmagan")
    
    text = f"{t['settings_menu']}\n\n⚽ Joriy jamoa: <b>{team}</b>"
    await message.answer(text, reply_markup=get_settings_inline(lang), parse_mode="HTML")

# --- INLINE CALLBACKS ---
@dp.callback_query(F.data == "set_team")
async def cb_set_team(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TRANSLATIONS[lang]
    await callback.message.edit_text(t["team_select"], reply_markup=get_teams_inline())

@dp.callback_query(F.data == "set_lang")
async def cb_set_lang(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TRANSLATIONS[lang]
    await callback.message.edit_text(t["lang_select"], reply_markup=get_langs_inline())

@dp.callback_query(F.data.startswith("team_"))
async def cb_save_team(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    team_name = callback.data.split("_")[1]
    
    if user_id not in user_settings:
        user_settings[user_id] = {"lang": "uz"}
    user_settings[user_id]["team"] = team_name
    
    lang = get_user_lang(user_id)
    t = TRANSLATIONS[lang]
    await callback.answer(t["saved"])
    await callback.message.edit_text(f"✅ Sevimli jamoa saqlandi: <b>{team_name}</b>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("lang_"))
async def cb_save_lang(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    new_lang = callback.data.split("_")[1]
    
    if user_id not in user_settings:
        user_settings[user_id] = {"team": "Tanlanmagan"}
    user_settings[user_id]["lang"] = new_lang
    
    t = TRANSLATIONS[new_lang]
    await callback.answer(t["saved"])
    
    # Yangi tildagi asosiy menyuni yuborish
    await callback.message.answer(t["welcome"].format(name=callback.from_user.first_name), reply_markup=get_main_keyboard(new_lang))

@dp.callback_query(F.data == "back_settings")
async def cb_back(callback: types.CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    t = TRANSLATIONS[lang]
    team = user_settings.get(callback.from_user.id, {}).get("team", "Tanlanmagan")
    text = f"{t['settings_menu']}\n\n⚽ Joriy jamoa: <b>{team}</b>"
    await callback.message.edit_text(text, reply_markup=get_settings_inline(lang), parse_mode="HTML")

# --- KUNLIK PROGNOZ ---
@dp.message(F.text.in_(["📊 Kunlik prognoz", "📊 Ежедневный прогноз", "📊 Daily Forecast"]))
async def daily_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    await message.answer(t["daily_text"], parse_mode="Markdown")

# --- AI PROGNOZ ---
@dp.message(F.text.in_(["🤖 AI Prognoz", "🤖 ИИ Прогноз", "🤖 AI Forecast"]))
async def ai_forecast(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    t = TRANSLATIONS[lang]
    
    await message.answer(t["ai_wait"])
    
    # Tanlangan tilga qarab AI'ga prompt berish
    prompt_langs = {
        "uz": "Bugungi kundagi eng muhim 5 ta futbol o'yini uchun professional tahlil va bashorat yoz. O'zbek tilida.",
        "ru": "Напиши профессиональный анализ и прогноз на топ-5 футбольных матчей на сегодня. На русском языке.",
        "en": "Write a professional analysis and prediction for the top 5 football matches for today. In English."
    }
    prompt = prompt_langs.get(lang, prompt_langs["uz"])
    
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
