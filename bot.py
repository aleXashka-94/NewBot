import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import csv
from collections import defaultdict
from aiohttp import web

# Конфигурация
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.getenv('PORT', 5000))

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
app = web.Application()

# Файлы данных
DATA_FILE = 'data.csv'
os.makedirs('data', exist_ok=True)
DATA_PATH = os.path.join('data', DATA_FILE)

# Состояния пользователей
user_states = {}
user_data = defaultdict(dict)

# Клавиатуры
def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Сегодня"), KeyboardButton("Вчера"))
    kb.add(KeyboardButton("Указать дату вручную"))
    return kb

def get_direction_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Туда", "Обратно")
    return kb

def get_type_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Поездом", "Пассажиром")
    return kb

# Обработчики сообщений
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери дату поездки:", reply_markup=get_main_keyboard())
    user_states[message.from_user.id] = 'waiting_for_date'

@dp.message_handler(lambda message: user_states.get(message.from_user.id) == 'waiting_for_date')
async def process_date(message: types.Message):
    user_id = message.from_user.id
    if message.text == "Сегодня":
        date = datetime.now().strftime("%Y-%m-%d")
    elif message.text == "Вчера":
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        try:
            date = datetime.strptime(message.text, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            await message.reply("Неверный формат даты. Введите в формате ГГГГ-ММ-ДД:")
            return
    
    user_data[user_id]['date'] = date
    user_states[user_id] = 'direction'
    await message.answer("Выберите направление:", reply_markup=get_direction_keyboard())

# ... (остальные обработчики остаются такими же, как в исходном коде)

# Функция сохранения данных
def save_to_csv(user_id):
    file_exists = os.path.isfile(DATA_PATH)
    with open(DATA_PATH, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Дата", "Направление", "Тип", "Явка", "Сдача", "Продолжительность", "Ночные часы"])
        row = [
            user_data[user_id]['date'],
            user_data[user_id]['direction'],
            user_data[user_id]['type'],
            user_data[user_id]['start_time'],
            user_data[user_id]['end_time'],
            user_data[user_id]['duration'],
            user_data[user_id]['night_hours'],
        ]
        writer.writerow(row)

# Вебхуки для Render
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    logging.warning('Shutting down..')
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning('Bye!')

# Запуск приложения
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    if os.getenv('RENDER'):
        # Режим для Render с вебхуками
        executor.start_webapp(
            dispatcher=dp,
            web_app=app,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )
    else:
        # Локальный режим с поллингом
        executor.start_polling(dp, skip_updates=True)