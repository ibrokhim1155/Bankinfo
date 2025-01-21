import logging
import asyncio
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message, FSInputFile
import sqlite3
from openpyxl import Workbook
from datetime import datetime

# Bot token
API_TOKEN = '7761975115:AAGwPBjxeUsotkvODRF3wjaaq3XXrGPGwrc'

# Initialize bot, dispatcher, and router
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()  # Yangi router yaratildi

# Database setup
conn = sqlite3.connect('citizens.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS citizens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    passport TEXT,
    address TEXT,
    family_size INTEGER,
    employed_count INTEGER,
    average_income REAL,
    has_pensioners BOOLEAN,
    unemployed_count INTEGER,
    poultry_count INTEGER,
    cattle_count INTEGER,
    sheep_count INTEGER,
    income_source TEXT,
    photos TEXT,
    registration_date DATE
)''')
conn.commit()

# Keyboards
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ro'yhatga olish"), KeyboardButton(text="Excelga yuklab olish")]
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Bekor qilish")]
    ],
    resize_keyboard=True
)

# States
user_data = {}

# Handlers
@router.message(F.text == "/start")
async def start_command(message: Message):
    await message.reply("Assalomu alaykum! Botga xush kelibsiz. Quyidagi menyudan foydalaning:", reply_markup=menu_kb)

@router.message(F.text == "Ro'yhatga olish")
async def register_citizen(message: Message):
    user_data[message.chat.id] = {}
    await message.reply("Fuqaroning to'liq ismini kiriting:", reply_markup=cancel_kb)

@router.message(F.text == "Bekor qilish")
async def cancel_action(message: Message):
    user_data.pop(message.chat.id, None)
    await message.reply("Amal bekor qilindi.", reply_markup=menu_kb)

@router.message(F.chat.id.in_(user_data.keys()))
async def collect_data(message: Message):
    chat_id = message.chat.id
    user_step = len(user_data[chat_id])

    steps = [
        "Fuqaroning pasport seriyasi va raqamini kiriting:",
        "Fuqaroning yashash manzilini kiriting:",
        "Oiladagi umumiy odamlar sonini kiriting:",
        "Oilada ishlayotgan odamlar sonini kiriting:",
        "Oylik o'rtacha daromadni kiriting:",
        "Pensionerlar bormi? (ha/yo'q):",
        "Mehnatga yaroqli lekin ishsiz odamlar sonini kiriting:",
        "Uyda nechta parranda borligini kiriting:",
        "Uyda nechta qoramol borligini kiriting:",
        "Uyda nechta qo'y borligini kiriting:",
        "Oilaning asosiy daromad manbasini kiriting:",
        "Fuqaroning rasmlarini jo'nating yoki 'skip' deb yozing:",
    ]

    if user_step < len(steps):
        if user_step == 11 and message.text.lower() != 'skip':
            user_data[chat_id]['photos'] = message.photo[-1].file_id if message.photo else None
        else:
            key = ['full_name', 'passport', 'address', 'family_size', 'employed_count', 'average_income', 'has_pensioners', 'unemployed_count', 'poultry_count', 'cattle_count', 'sheep_count', 'income_source'][user_step]
            user_data[chat_id][key] = message.text

        if len(user_data[chat_id]) < len(steps):
            await message.reply(steps[user_step])
        else:
            # Save data to the database
            cursor.execute('''INSERT INTO citizens (
                full_name, passport, address, family_size, employed_count, 
                average_income, has_pensioners, unemployed_count, poultry_count, 
                cattle_count, sheep_count, income_source, photos, registration_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_data[chat_id].get('full_name'),
                user_data[chat_id].get('passport'),
                user_data[chat_id].get('address'),
                int(user_data[chat_id].get('family_size', 0)),
                int(user_data[chat_id].get('employed_count', 0)),
                float(user_data[chat_id].get('average_income', 0.0)),
                user_data[chat_id].get('has_pensioners') == 'ha',
                int(user_data[chat_id].get('unemployed_count', 0) or 0),
                int(user_data[chat_id].get('poultry_count', 0)),
                int(user_data[chat_id].get('cattle_count', 0)),
                int(user_data[chat_id].get('sheep_count', 0)),
                user_data[chat_id].get('income_source'),
                user_data[chat_id].get('photos'),
                datetime.now().date()
            ))
            conn.commit()
            user_data.pop(chat_id)
            await message.reply("Ma'lumotlar muvaffaqiyatli saqlandi.", reply_markup=menu_kb)

@router.message(F.text == "Excelga yuklab olish")
async def download_excel(message: Message):
    await message.reply("Iltimos, ma'lumotlarni yuklash uchun vaqt oralig'ini kiriting. Format: YYYY-MM-DD YYYY-MM-DD")

    @router.message()
    async def handle_date_input(date_message: Message):
        try:
            start_date, end_date = date_message.text.split()
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            cursor.execute("SELECT * FROM citizens WHERE registration_date BETWEEN ? AND ?", (start_date, end_date))
            rows = cursor.fetchall()

            workbook = Workbook()
            sheet = workbook.active
            headers = [desc[0] for desc in cursor.description]
            sheet.append(headers)
            for row in rows:
                sheet.append(row)

            excel_file_path = "../.venv/citizens_data.xlsx"
            workbook.save(excel_file_path)

            await date_message.answer_document(
                document=FSInputFile(excel_file_path),
                caption="Ma'lumotlaringiz tayyor."
            )
        except ValueError:
            await date_message.reply("Noto'g'ri format! Iltimos, vaqt oralig'ini to'g'ri kiriting. Format: YYYY-MM-DD YYYY-MM-DD")

# Main function
async def main():
    logging.basicConfig(level=logging.INFO)
    dp.include_router(router)  # Routerni Dispatcherga qo'shing
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())