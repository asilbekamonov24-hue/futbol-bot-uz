import asyncio
import logging
import os
import google.generativeai as genai
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# --- SOZLAMALAR (Render muhitidan o'qiydi) ---
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini API ni sozlash
genai.configure(api_key=GEMINI_API_KEY)

# Bot va Dispatcher yaratish
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- KLAVIATURA ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Kunlik prognoz"),
                KeyboardButton(text="🤖 AI Prognoz")
            ]
        ],
        resize_keyboard=True
    )

# --- START BUYRUG'I ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name
    text = (
        f"Salom, {user_name}! Futbol prognoz botiga xush kelibsiz.\n"
        f"Quyidagi tugmalardan birini tanlang:"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# --- KUNLIK PROGNOZ ---
@dp.message(F.text == "📊 Kunlik prognoz")
async def daily_forecast(message: types.Message):
    await message.answer("📊 **Bugungi kunlik prognoz:**\n\nReal vs Barcelona - Bugun barca g'alaba qozonishi kutilmoqda")

# --- AI PROGNOZ (5 TA O'YIN TAHLILI) ---
@dp.message(F.text == "🤖 AI Prognoz")
async def ai_forecast(message: types.Message):
    await message.answer("⏳ Sun'iy intellekt bugungi eng yaxshi 5 ta futbol o'yinini tahlil qilmoqda, biroz kuting...")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            "Bugungi kundagi eng muhim yoki mashhur 5 ta futbol o'yini uchun professional bashorat va tahlil tuzib ber. "
            "Har bir o'yin uchun jamoalar nomi, taxminiy natija va qisqacha tahlil yoz. "
            "Javobni chiroyli va tushunarli formatda O'zbek tilida taqdim et."
        )
        response = model.generate_content(prompt)
        ai_text = response.text
        
        if len(ai_text) > 4000:
            ai_text = ai_text[:4000]
            
        await message.answer(f"🤖 **Sun'iy Intellekt Tahlili (Top 5 O'yin):**\n\n{ai_text}")
    except Exception as e:
        await message.answer("❌ AI tahlilini olishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.")

# --- RENDER UCHUN WEB SERVER ---
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

# --- ASOSIY FUNKSIYA ---
async def main():
    asyncio.create_task(web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
