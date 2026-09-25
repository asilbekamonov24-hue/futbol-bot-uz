import asyncio
import logging
import sys
import sqlite3
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
import google.generativeai as genai

TOKEN = os.getenv("TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR else None

if not TOKEN or not ADMIN_ID or not GEMINI_API_KEY:
    logging.error("XATOLIK: TOKEN, ADMIN_ID yoki GEMINI_API_KEY topilmadi!")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")

def init_db():
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecasts (
                forecast_type TEXT PRIMARY KEY,
                content TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"DB xatolik: {e}")

def add_user(user_id: int, full_name: str):
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?, ?)", (user_id, full_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"User xatolik: {e}")

def get_forecasti(f_type: str):
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM forecasts WHERE forecast_type = ?", (f_type,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"Read xatolik: {e}")
        return None

init_db()

asosiy_menyu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Kunlik prognoz"), KeyboardButton(text="🤖 AI Tahlil")]
    ],
    resize_keyboard=True
)

dp = Dispatcher()

@dp.message(CommandStart())
async def buyruq_boshlash(message: Message) -> None:
    try:
        add_user(message.from_user.id, message.from_user.full_name or "Foydalanuvchi")
        await message.answer(
            f"Salom, {html.quote(message.from_user.first_name)}! Futbol prognoz botiga xush kelibsiz.\nQuyidagi tugmalardan birini tanlang:",
            reply_markup=asosiy_menyu
        )
    except Exception as e:
        logging.error(f"Start xatolik: {e}")

@dp.message(Command('ai_ornatish'))
async def ai_tahlil_yaratish(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda huquq yo'q!")
        return

    prompt = message.text.replace("/ai_ornatish", "").strip()
    if not prompt:
        prompt = "Futbol bo'yicha bugungi o'yinlar uchun professional tahlil tuzib ber."

    waiting_msg = await message.answer("🤖 AI tahlil tayyorlamoqda...")
    try:
        response = ai_model.generate_content(prompt)
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO forecasts (forecast_type, content) VALUES (?, ?)", ("ai_tahlil", response.text))
        conn.commit()
        conn.close()
        await waiting_msg.edit_text("✅ AI tahlil tayyorlandi va bazaga saqlandi!")
    except Exception as e:
        await waiting_msg.edit_text(f"❌ Xatolik: {e}")

@dp.message()
async def matn_ishlovchisi(message: Message) -> None:
    if message.text == "📅 Kunlik prognoz":
        matn = get_forecasti("kundalik")
        await message.answer(matn if matn else "⏳ Hozircha kunlik prognoz yo'q.")
    elif message.text == "🤖 AI Tahlil":
        matn = get_forecasti("ai_tahlil")
        await message.answer(matn if matn else "⏳ Hozircha AI tahlil yo'q.")
    else:
        await message.answer("Iltimos, pastdagi tugmalardan foydalaning.")

async def handle(request):
    return web.Response(text="Bot ishlayapti!")

app = web.Application()
app.add_routes([web.get("/", handle)])

async def web_app():
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print("Bot muvaffaqiyatli ishga tushdi...")
    await asyncio.gather(web_app(), dp.start_polling(bot))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
