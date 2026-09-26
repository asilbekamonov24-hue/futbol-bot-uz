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

# Bazis foydalanuvchilar bazasini saqlash uchun to'plam (Set)
users_db = set()

# --- ASOSIY KLAVIATURA ---
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Kunlik prognoz"),
                KeyboardButton(text="🤖 AI Prognoz")
            ],
            [
                KeyboardButton(text="ℹ️ Yordam (/help)"),
                KeyboardButton(text="⚙️ Sozlamalar (/settings)")
            ]
        ],
        resize_keyboard=True
    )

# --- INLINE SOZLAMALAR KLAVIaturasi ---
def get_settings_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚽ Sevimli jamoani tanlash", callback_data="set_team")
            ],
            [
                InlineKeyboardButton(text="🌐 Tilni o'zgartirish", callback_data="set_lang")
            ]
        ]
    )

# --- START BUYRUG'I ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    users_db.add(user_id)  # Foydalanuvchini bazaga qo'shish
    
    user_name = message.from_user.first_name
    text = (
        f"Salom, {user_name}! Futbol prognoz botiga xush kelibsiz.\n"
        f"Quyidagi tugmalardan birini tanlang yoki buyruqlardan foydalaning:"
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# --- HELP BUYRUG'I ---
@dp.message(Command("help"))
@dp.message(F.text == "ℹ️ Yordam (/help)")
async def cmd_help(message: types.Message):
    help_text = (
        "🤖 **Botdan foydalanish bo'yicha qo'llanma:**\n\n"
        "• **/start** - Botni qayta ishga tushirish va menyuni ochish.\n"
        "• **/stat** - Botdagi jami foydalanuvchilar statistikasini ko'rish.\n"
        "• **/settings** - Til va sevimli jamoalarni sozlash.\n"
        "• **📊 Kunlik prognoz** - Kun ichidagi asosiy o'yin uchun qisqacha bashorat.\n"
        "• **🤖 AI Prognoz** - Sun'iy intellekt orqali eng yaxshi 5 ta o'yin tahlilini olish."
    )
    await message.answer(help_text, parse_mode="Markdown")

# --- STAT BUYRUG'I (Statistika) ---
@dp.message(Command("stat"))
async def cmd_stat(message: types.Message):
    total_users = len(users_db)
    await message.answer(f"📊 **Bot statistikasi:**\n\nJami foydalanuvchilar soni: {total_users} ta")

# --- SETTINGS BUYRUG'I ---
@dp.message(Command("settings"))
@dp.message(F.text == "⚙️ Sozlamalar (/settings)")
async def cmd_settings(message: types.Message):
    await message.answer("⚙️ **Sozlamalar bo'limi:**\nKerakli parametrni tanlang:", reply_markup=get_settings_inline())

# --- INLINE TUGMALAR BILAN ISHLASH ---
@dp.callback_query(F.data == "set_team")
async def callback_team(callback: types.CallbackQuery):
    await callback.answer("Tez kunda: Sevimli jamoani tanlash imkoniyati qo'shiladi!")
    await callback.message.answer("⚽ Hozircha bu funksiya ishlab chiqish jarayonida. Tez orada sevimli klubingizni tanlay olasiz!")

@dp.callback_query(F.data == "set_lang")
async def callback_lang(callback: types.CallbackQuery):
    await callback.answer("Hozircha faqat O'zbek tili mavjud.")
    await callback.message.answer("🌐 Bot hozircha faqat O'zbek tilida ishlaydi.")

# --- KUNLIK PROGNOZ ---
@dp.message(F.text == "📊 Kunlik prognoz")
async def daily_forecast(message: types.Message):
    await message.answer("📊 **Bugungi kunlik prognoz:**\n\nReal vs Barcelona - Bugun barca g'alaba qozonishi kutilmoqda")

# --- AI PROGNOZ (REST API ORQALI) ---
@dp.message(F.text == "🤖 AI Prognoz")
async def ai_forecast(message: types.Message):
    await message.answer("⏳ Sun'iy intellekt bugungi eng yaxshi 5 ta futbol o'yinini tahlil qilmoqda, biroz kuting...")
    
    prompt = (
        "Bugungi kundagi eng muhim yoki mashhur 5 ta futbol o'yini uchun professional bashorat va tahlil tuzib ber. "
        "Har bir o'yin uchun jamoalar nomi, taxminiy natija va qisqacha tahlil yoz. "
        "Javobni chiroyli va tushunarli formatda O'zbek tilida taqdim et."
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    if len(ai_text) > 4000:
                        ai_text = ai_text[:4000]
                    await message.answer(f"🤖 **Sun'iy Intellekt Tahlili (Top 5 O'yin):**\n\n{ai_text}")
                else:
                    err_text = await response.text()
                    print(f"API Xatolik: {err_text}")
                    await message.answer("❌ AI tahlilini olishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.")
    except Exception as e:
        print(f"Ulanish xatosi: {e}")
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
