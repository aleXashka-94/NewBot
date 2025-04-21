import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import csv
from collections import defaultdict
import os

API_TOKEN = 'YOUR_TOKEN_HERE'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

data_file = 'data.csv'

user_states = {}
user_data = defaultdict(dict)

# Основная клавиатура
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("Сегодня"), KeyboardButton("Вчера"))
main_kb.add(KeyboardButton("Указать дату вручную"))

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери дату поездки:", reply_markup=main_kb)
    user_states[message.from_user.id] = 'waiting_for_date'

@dp.message_handler(lambda message: user_states.get(message.from_user.id) == 'waiting_for_date')
async def get_date(message: types.Message):
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
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Туда", "Обратно")
    await message.answer("Выберите направление:", reply_markup=kb)

@dp.message_handler(lambda message: user_states.get(message.from_user.id) == 'direction')
async def get_direction(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]['direction'] = message.text
    user_states[user_id] = 'type'
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Поездом", "Пассажиром")
    await message.answer("Выберите тип поездки:", reply_markup=kb)

@dp.message_handler(lambda message: user_states.get(message.from_user.id) == 'type')
async def get_type(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]['type'] = message.text
    user_states[user_id] = 'start_time'
    await message.answer("Введите время явки (в формате ЧЧ:ММ):")

@dp.message_handler(lambda message: user_states.get(message.from_user.id) == 'start_time')
async def get_start_time(message: types.Message):
    user_id = message.from_user.id
    try:
        start_time = datetime.strptime(message.text, "%H:%M")
        user_data[user_id]['start_time'] = message.text
        user_states[user_id] = 'end_time'
        await message.answer("Введите время сдачи (в формате ЧЧ:ММ):")
    except ValueError:
        await message.answer("Неверный формат времени. Введите в формате ЧЧ:ММ.")

@dp.message_handler(lambda message: user_states.get(message.from_user.id) == 'end_time')
async def get_end_time(message: types.Message):
    user_id = message.from_user.id
    try:
        end_time = datetime.strptime(message.text, "%H:%M")
        start_time = datetime.strptime(user_data[user_id]['start_time'], "%H:%M")
        user_data[user_id]['end_time'] = message.text

        # Расчёт продолжительности
        if end_time < start_time:
            end_time += timedelta(days=1)
        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600
        user_data[user_id]['duration'] = round(duration_hours, 2)

        # Расчёт ночных часов (22:00–06:00)
        night_hours = 0
        current = start_time
        while current < end_time:
            if current.hour >= 22 or current.hour < 6:
                night_hours += 1
            current += timedelta(hours=1)
        user_data[user_id]['night_hours'] = night_hours

        # Сохраняем данные в CSV
        save_to_csv(user_id)
        await message.answer(f"Поездка сохранена:
Дата: {user_data[user_id]['date']}
"
                             f"Направление: {user_data[user_id]['direction']}
Тип: {user_data[user_id]['type']}
"
                             f"Явка: {user_data[user_id]['start_time']}
Сдача: {user_data[user_id]['end_time']}
"
                             f"Продолжительность: {user_data[user_id]['duration']} ч
Ночных часов: {user_data[user_id]['night_hours']} ч")
        user_states[user_id] = None
        user_data[user_id] = {}
    except ValueError:
        await message.answer("Неверный формат времени. Введите в формате ЧЧ:ММ.")

def save_to_csv(user_id):
    file_exists = os.path.isfile(data_file)
    with open(data_file, mode='a', newline='', encoding='utf-8') as f:
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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)