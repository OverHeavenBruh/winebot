import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Инициализация базы данных
conn = sqlite3.connect("wines.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS wines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        quantity INTEGER
    )
""")
conn.commit()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот склада. Используй /add и /list.")

# Команда /add название количество (например: /add Мерло 3)
async def add_wine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) >= 1:
        name = context.args[0]
        quantity = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 1

        cursor.execute("SELECT quantity FROM wines WHERE name = ?", (name,))
        result = cursor.fetchone()
        if result:
            new_quantity = result[0] + quantity
            cursor.execute("UPDATE wines SET quantity = ? WHERE name = ?", (new_quantity, name))
        else:
            cursor.execute("INSERT INTO wines (name, quantity) VALUES (?, ?)", (name, quantity))
        conn.commit()
        await update.message.reply_text(f"✅ Добавлено: {name} (+{quantity})")
    else:
        await update.message.reply_text("Используй так: /add Название [Количество]")

# Команда /list
async def list_wines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT name, quantity FROM wines")
    rows = cursor.fetchall()
    if rows:
        text = "\n".join(f"- {name}: {qty} шт." for name, qty in rows)
        await update.message.reply_text(f"📦 Вина на складе:\n{text}")
    else:
        await update.message.reply_text("Склад пуст.")

# Основной запуск
app = ApplicationBuilder().token("ТВОЙ_ТОКЕН").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_wine))
app.add_handler(CommandHandler("list", list_wines))

app.run_polling()
