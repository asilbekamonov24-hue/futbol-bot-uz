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

TOKEN = "8725274573:AAEvuyrQ_hk6hNBilQqC1eAa_15c27wwA"
ADMIN_ID = 703706449

def init_db():
    conn = sqlite3.connect("futbol_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            forecast_type TEXT PRIMARY KEY,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_forecast(f_type: str, content: str):
    conn = sqlite3.connect("futbol_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("""
        REPLACE INTO forecasts (forecast_type, content) 
        VALUES (?, ?)
    """, (f_type, content))
    conn.commit()
    conn.close()

def get_forecasti(f_type: str):
    conn = sqlite3.connect("futbol_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM forecasts WHERE forecast_type = ?", (f_type,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

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
    foydalanuvchi_nomi = html.iqtibos(message.from_user.first_name)
    await message.answer(
        f"Salom, {foydalanuvchi_nomi}! Futbol prognoz botiga xush kelibsiz.\n"
        f"Quyidagi tugmalardan birini tanlang:",
        reply_markup=asosiy_menyu
    )

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
    print("Bot ma'lumotlar bazasi bilan ishga tushdi va uxlab qolmaydi...")
    await asyncio.gather(web_app(), dp.start_polling(bot))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
