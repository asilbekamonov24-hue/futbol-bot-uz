import asyncio
import logging
import sys
import sqlite3
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# Bot tokeningizni shu yerga yozasiz
TOKEN = "8725274573:AAEVuyrQ_hK6bHNBilQqClteAa_15c27wwA"

# O'zingizning Telegram ID raqamingizni yozasiz
ADMIN_ID = 7035706449  # <--- O'z ID raqamingizni yozing!

# --- BAZA BILAN ISHLASH QISMI ---
def init_db():
    conn = sqlite3.connect("futbol_bazasi.db")
    cursor = conn.cursor()
    # Prognozlarni saqlash uchun jadval yaratamiz
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
        INSERT OR REPLACE INTO forecasts (forecast_type, content)
        VALUES (?, ?)
    """, (f_type, content))
    conn.commit()
    conn.close()

def get_forecast(f_type: str):
    conn = sqlite3.connect("futbol_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM forecasts WHERE forecast_type = ?", (f_type,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# Dastur ishga tushganda bazani tayyorlab qo'yamiz
init_db()

# Foydalanuvchi uchun asosiy menyu tugmalari
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Kunlik prognoz"), KeyboardButton(text="📆 Haftalik prognoz")]
    ],
    resize_keyboard=True
)

dp = Dispatcher()

# /start komandasi
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_name = html.quote(message.from_user.first_name)
    await message.answer(
        f"Salom, {user_name}! Futbol prognoz botiga xush kelibsiz.\n"
        f"Quyidagi tugmalardan birini tanlang:",
        reply_markup=main_menu
    )

# --- ADMIN QISMI ---
@dp.message(Command("set_daily"))
async def set_daily_forecast(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruqni ishlatish huquqi yo'q!")
        return
    
    text = message.text.replace("/set_daily", "").strip()
    if not text:
        await message.answer("Iltimos, prognoz matnini ham yozing! Masalan:\n`/set_daily Real vs Barcelona - G'alaba 1`")
        return
    
    # Bazaga saqlaymiz
    save_forecast("daily", text)
    await message.answer("✅ Kunlik prognoz bazaga saqlandi va foydalanuvchilarga ochildi!")

@dp.message(Command("set_weekly"))
async def set_weekly_forecast(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Sizda bu buyruqni ishlatish huquqi yo'q!")
        return
    
    text = message.text.replace("/set_weekly", "").strip()
    if not text:
        await message.answer("Iltimos, haftalik prognoz matnini ham yozing!")
        return
    
    # Bazaga saqlaymiz
    save_forecast("weekly", text)
    await message.answer("✅ Haftalik prognoz bazaga saqlandi!")


# --- FOYDALANUVCHI TUGMALARI ---
@dp.message()
async def text_handler(message: Message) -> None:
    if message.text == "📅 Kunlik prognoz":
        daily_text = get_forecast("daily")
        if daily_text is None:
            await message.answer("⏳ Bugungi o'yinlar hali tahlil qilinmoqda, birozdan so'ng tekshiring.")
        else:
            await message.answer(f"📊 **Bugungi kunlik prognoz:**\n\n{daily_text}")
            
    elif message.text == "📆 Haftalik prognoz":
        weekly_text = get_forecast("weekly")
        if weekly_text is None:
            await message.answer("⏳ Haftalik o'yinlar hali tahlil qilinmoqda, birozdan so'ng tekshiring.")
        else:
            await message.answer(f"📅 **Haftalik prognoz:**\n\n{weekly_text}")
    else:
        await message.answer("Iltimos, pastdagi tugmalardan foydalaning.")

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    print("Bot ma'lumotlar bazasi bilan ishga tushdi va uxlab qolmaydi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())