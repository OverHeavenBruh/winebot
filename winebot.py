from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Простой список вин (можно заменить на базу данных позже)
wine_list = []

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот-склад вина. Используй /add и /list.")

# Команда /list
async def list_wines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if wine_list:
        wines = '\n'.join(f"- {w}" for w in wine_list)
        await update.message.reply_text(f"📦 Вина на складе:\n{wines}")
    else:
        await update.message.reply_text("Пока склад пуст.")

# Команда /add <название вина>
async def add_wine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        wine_name = ' '.join(context.args)
        wine_list.append(wine_name)
        await update.message.reply_text(f"✅ Добавлено: {wine_name}")
    else:
        await update.message.reply_text("Пиши так: /add Название Вина")

# Основной запуск
app = ApplicationBuilder().token("7259879117:AAER7Z6RczPQ0beeuUiQLcieq0_nhYHDODg").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("list", list_wines))
app.add_handler(CommandHandler("add", add_wine))

app.run_polling()
