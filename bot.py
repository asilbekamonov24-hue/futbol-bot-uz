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
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, PollAnswer

# Xavfsizlik uchun Token va Admin ID Render Environment Variables'dan o'qiladi
TOKEN = os.getenv("TOKEN")
ADMIN_ID_STR = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID_STR) if ADMIN_ID_STR else None

if not TOKEN or not ADMIN_ID:
    logging.error("XATOLIK: TOKEN yoki ADMIN_ID topilmadi! Render Environment Variables'ni tekshiring.")
    sys.exit(1)

def init_db():
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        # Prognozlar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecasts (
                forecast_type TEXT PRIMARY KEY,
                content TEXT
            )
        """)
        # Foydalanuvchilar bazasi (Statistika va Broadcast uchun)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Ma'lumotlar bazasini yaratishda xatolik: {e}")

def add_user(user_id: int, full_name: str):
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, full_name) 
            VALUES (?, ?)
        """, (user_id, full_name))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Foydalanuvchini qo'shishda xatolik: {e}")

def get_total_users():
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logging.error(f"Foydalanuvchilar sonini olishda xatolik: {e}")
        return 0

def get_all_users():
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    except Exception as e:
        logging.error(f"Foydalanuvchilar ro'yxatini olishda xatolik: {e}")
        return []

def save_forecast(f_type: str, content: str):
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("""
            REPLACE INTO forecasts (forecast_type, content) 
            VALUES (?, ?)
        """, (f_type, content))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Prognozni saqlashda xatolik: {e}")

def get_forecasti(f_type: str):
    try:
        conn = sqlite3.connect("futbol_bazasi.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM forecasts WHERE forecast_type = ?", (f_type,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"Prognozni o'qishda xatolik: {e}")
        return None

init_db()

asosiy_menyu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Kunlik prognoz"), KeyboardButton(text="📅 Haftalik prognoz")]
    ],
    resize_keyboard=True
)

dp = Dispatcher()

@dp.message(CommandStart())
async def buyruq_boshlash_ishlovchisi(message: Message) -> None:
    try:
        user_id = message.from_user.id
        full_name = message.from_user.full_name or "Foydalanuvchi"
        add_user(user_id, full_name)

        foydalanuvchi_nomi = html.quote(message.from_user.first_name)
        await message.answer(
            f"Salom, {foydalanuvchi_nomi}! Futbol prognoz botiga xush kelibsiz.\n"
            f"Quyidagi tugmalardan birini tanlang:",
            reply_markup=asosiy_menyu
        )
    except Exception as e:
        logging.error(f"Start buyrug'ida xatolik: {e}")

# 1. Foydalanuvchilar statistikasi (/stat)
@dp.message(Command('stat'))
async def bot_statistikasi(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruq uchun huquq yo'q!")
        return
    
    total = get_total_users()
    await message.answer(f"📊 **Bot statistikasi:**\n\nJami foydalanuvchilar soni: <b>{total}</b> ta")

# 2. Ovoz berish yaratish (/poll) - Admin buyrug'i
@dp.message(Command('poll'))
async def create_poll(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruq uchun huquq yo'q!")
        return

    # Masalan: /poll Real Madrid - Barcelona|Real yutadi|Barcelona yutadi|Durang
    text = message.text.replace("/poll", "").strip()
    if not text or "|" not in text:
        await message.answer(
            "Iltimos, to'g'ri formatda yozing:\n"
            "<code>/poll Savol matni?|Variant 1|Variant 2|Variant 3</code>"
        )
        return

    parts = [p.strip() for p in text.split("|")]
    question = parts[0]
    options = parts[1:]

    if len(options) < 2:
        await message.answer("Kamida 2 ta variant bo'lishi kerak!")
        return

    try:
        await message.bot.send_poll(
            chat_id=message.chat.id,
            question=question,
            options=options,
            is_anonymous=False
        )
    except Exception as e:
        await message.answer(f"Ovoz berishni ochishda xatolik: {e}")

# 3. Barchaga xabar yuborish (Broadcast)
@dp.message(Command('broadcast'))
async def broadcast_message(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruq uchun huquq yo'q!")
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("Iltimos, yubormoqchi bo'lgan xabar matnini yozing!\nMisol: <code>/broadcast E'lon: Bugun muhim o'yin bor!</code>")
        return

    users = get_all_users()
    success = 0
    failed = 0

    await message.answer(f"⏳ Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")

    for uid in users:
        try:
            await message.bot.send_message(chat_id=uid, text=f"📢 <b>E'lon:</b>\n\n{text}")
            success += 1
            await asyncio.sleep(0.05) # Telegram limitiga tushmaslik uchun kichik tanaffus
        except Exception:
            failed += 1

    await message.answer(f"✅ Xabar tarqatildi!\n\n• Muvaffaqiyatli: {success}\n• Xatolik (bloklaganlar): {failed}")

@dp.message(Command('kundalik_ornatish'))
async def kundalik_baholashni_ornatish(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruq uchun huquq yo'q!")
        return

    matn = message.text.replace("/kundalik_ornatish", "").strip()
    if not matn:
        await message.answer("Iltimos, prognoz matnini ham yozing! Masalan:\n/kundalik_ornatish Real vs Barcelona - G'alaba 1")
        return

    save_forecast("kundalik", matn)
    await message.answer("✅ Kunlik prognoz bazaga saqlandi va foydalanuvchilarga ochildi!")

@dp.message(Command('haftalik_toplam'))
async def haftalik_prognozni_belgilash(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruq uchun huquq yo'q!")
        return

    matn = message.text.replace("/haftalik_toplam", "").strip()
    if not matn:
        await message.answer("Iltimos, haftalik prognoz matnini ham yozing!")
        return

    save_forecast("haftalik", matn)
    await message.answer("✅ Haftalik prognoz bazaga saqlandi!")

@dp.message()
async def matn_ishlovchisi(message: Message) -> None:
    try:
        if message.text == "📅 Kunlik prognoz":
            kundalik_matn = get_forecasti("kundalik")
            if kundalik_matn is None:
                await message.answer("⏳ Bugun o'yinlar hali tahlil qilinmoqda, birozdan so'ng tekshiring.")
            else:
                await message.answer(f"📊 **Bugungi kunlik prognoz:**\n\n{kundalik_matn}")

        elif message.text == "📅 Haftalik prognoz":
            haftalik_matn = get_forecasti("haftalik")
            if haftalik_matn is None:
                await message.answer("⏳ Haftalik o'yinlar hali tahlil qilinmoqda, birozdan so'ng.")
            else:
                await message.answer(f"📊 **Haftalik prognoz:**\n\n{haftalik_matn}")
        else:
            await message.answer("Iltimos, pastdagi tugmalardan foydalaning.")
    except Exception as e:
        logging.error(f"Matn ishlovchisida xatolik: {e}")

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
    print("Bot yangi funksiyalar bilan xavfsiz rejimda ishga tushdi...")
    await asyncio.gather(web_app(), dp.start_polling(bot))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
