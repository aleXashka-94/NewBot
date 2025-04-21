
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = "7202762947:AAGQHuyAdD_mNoUGzmkeCBblcVbxbOjgWsA"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

CHOOSING_DIRECTION, CHOOSING_TYPE, ENTER_TIME, MENU = range(4)
user_data_store = {}

reply_main = ReplyKeyboardMarkup([['Поездка туда', 'Поездка обратно']], one_time_keyboard=True, resize_keyboard=True)
reply_type = ReplyKeyboardMarkup([['Поездом', 'Пассажиром']], one_time_keyboard=True, resize_keyboard=True)
reply_date = ReplyKeyboardMarkup([['Сегодня', 'Вчера', 'Указать дату']], one_time_keyboard=True, resize_keyboard=True)

def parse_time(date_str, time_str):
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выбери направление поездки:", reply_markup=reply_main)
    return CHOOSING_DIRECTION

async def choose_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["direction"] = update.message.text
    await update.message.reply_text("Выбери тип поездки:", reply_markup=reply_type)
    return CHOOSING_TYPE

async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["type"] = update.message.text
    await update.message.reply_text("Укажи дату явки:", reply_markup=reply_date)
    context.user_data["step"] = "start_date"
    return ENTER_TIME

async def enter_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    now = datetime.now()
    if text == "Сегодня":
        date = now.strftime("%Y-%m-%d")
    elif text == "Вчера":
        date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    elif context.user_data["step"] == "manual_date":
        date = context.user_data["manual_date"]
    elif context.user_data["step"] == "start_date":
        context.user_data["manual_date"] = text
        context.user_data["step"] = "manual_date"
        await update.message.reply_text("Теперь введи время в формате ЧЧ:ММ")
        return ENTER_TIME
    else:
        await update.message.reply_text("Теперь введи время в формате ЧЧ:ММ")
        context.user_data["manual_date"] = text
        context.user_data["step"] = "manual_date"
        return ENTER_TIME

    if context.user_data["step"] == "start_date":
        context.user_data["start_date"] = date
        context.user_data["step"] = "start_time"
        await update.message.reply_text("Введи время явки (например, 08:00):")
        return ENTER_TIME
    elif context.user_data["step"] == "start_time":
        start_time = parse_time(context.user_data["start_date"], text)
        if start_time:
            context.user_data["start_time"] = start_time
            context.user_data["step"] = "end_date"
            await update.message.reply_text("Укажи дату сдачи:", reply_markup=reply_date)
        else:
            await update.message.reply_text("Неверный формат времени.")
        return ENTER_TIME
    elif context.user_data["step"] == "end_date":
        context.user_data["end_date"] = date
        context.user_data["step"] = "end_time"
        await update.message.reply_text("Введи время сдачи (например, 19:00):")
        return ENTER_TIME
    elif context.user_data["step"] == "end_time":
        end_time = parse_time(context.user_data["end_date"], text)
        if end_time:
            context.user_data["end_time"] = end_time
            return await finish(update, context)
        else:
            await update.message.reply_text("Неверный формат времени.")
        return ENTER_TIME

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = context.user_data["start_time"]
    end = context.user_data["end_time"]
    direction = context.user_data["direction"]
    t_type = context.user_data["type"]

    duration = end - start
    hours = duration.total_seconds() / 3600

    # Расчёт ночных часов
    night_hours = 0
    temp = start
    while temp < end:
        if temp.hour >= 22 or temp.hour < 6:
            night_hours += 1
        temp += timedelta(hours=1)

    # Сохраняем поездку
    user_id = update.effective_user.id
    if user_id not in user_data_store:
        user_data_store[user_id] = []
    user_data_store[user_id].append({
        "direction": direction,
        "type": t_type,
        "start": start,
        "end": end,
        "hours": round(hours, 2),
        "night_hours": night_hours
    })

    await update.message.reply_text(
        f"Поездка сохранена":
"
        f"Тип": {t_type}, Направление: {direction}
"
        f"Явка": {start}, Сдача: {end}
"
        f"Всего часов": {round(hours, 2)}
"
        f"Ночных часов": {night_hours}"
    )
    return await start(update, context)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_DIRECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_direction)],
            CHOOSING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            ENTER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_time)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.run_polling()
