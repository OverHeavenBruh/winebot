import os
import logging
import psycopg2
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Подключение к PostgreSQL
conn = psycopg2.connect(
    host=os.environ["PGHOST"],
    database=os.environ["PGDATABASE"],
    user=os.environ["PGUSER"],
    password=os.environ["PGPASSWORD"],
    port=os.environ.get("PGPORT", 5432)
)
cur = conn.cursor()

# Создаём таблицу, если нет
cur.execute('''
    CREATE TABLE IF NOT EXISTS wines (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL
    );
''')
conn.commit()


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот склада вина. Используй /add и /list.")


# Команда /add Название Кол-во
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        name = context.args[0]
        quantity = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Пример: /add Мерло 5")
        return

    cur.execute("SELECT quantity FROM wines WHERE name = %s", (name,))
    result = cur.fetchone()

    if result:
        cur.execute("UPDATE wines SET quantity = quantity + %s WHERE name = %s", (quantity, name))
    else:
        cur.execute("INSERT INTO wines (name, quantity) VALUES (%s, %s)", (name, quantity))

    conn.commit()
    await update.message.reply_text(f"Добавлено: {name} — {quantity} шт.")


# Команда /list
async def list_wines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT name, quantity FROM wines ORDER BY name")
    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("Склад пуст.")
        return

    msg = "\n".join([f"{name}: {qty} шт." for name, qty in rows])
    await update.message.reply_text(msg)


# Запуск бота
if __name__ == "__main__":
    token = os.environ["BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_wines))

    logging.info("Bot started...")
    app.run_polling()
