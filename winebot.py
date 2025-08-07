import os
import logging
import psycopg2
import tempfile
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

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

# Таблица вин
cur.execute('''
    CREATE TABLE IF NOT EXISTS wines (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        sealed_lobby INTEGER,
        sealed_letnik INTEGER,
        open_lobby INTEGER,
        open_letnik INTEGER,
        photo BYTEA
    );
''')
conn.commit()

# Шаги диалога
(ASK_SEALED_LOBBY, ASK_SEALED_LETNIK, ASK_OPEN_LOBBY, ASK_OPEN_LETNIK, ASK_PHOTO) = range(5)
wine_data = {}

# Шаги update
(ASK_UPDATE_SELECT, ASK_UPDATE_SEALED_LOBBY, ASK_UPDATE_SEALED_LETNIK, ASK_UPDATE_OPEN_LOBBY, ASK_UPDATE_OPEN_LETNIK, ASK_UPDATE_PHOTO) = range(10, 16)
update_state = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /add для добавления вина.")

# Команда /list
async def list_wines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT name, sealed_lobby, sealed_letnik, open_lobby, open_letnik, photo FROM wines ORDER BY name")
    rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("Склад пуст.")
        return

    for row in rows:
        name, sl, st, ol, ot, photo = row
        sl = sl if sl else 0
        st = st if st else 0
        ol = ol if ol else 0
        ot = ot if ot else 0

        lobby_info = f"Открыто: {ol} Закрыто: {sl}" if ol or sl else "Отсутствует"
        letnik_info = f"Открыто: {ot} Закрыто: {st}" if ot or st else "Отсутствует"

        if lobby_info == "Отсутствует" and letnik_info == "Отсутствует":
            msg = f"{name}:\nВино полностью отсутствует."
        else:
            msg = f"{name}:\nLobby:\n{lobby_info}\nЛетник:\n{letnik_info}"

        await update.message.reply_text(msg)

        # Отправка фото, если есть
        if photo:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(photo)
                tmp_path = tmp.name
            with open(tmp_path, 'rb') as f:
                await update.message.reply_photo(photo=InputFile(f))

# Команда /add
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /add Мерло")
        return ConversationHandler.END
    wine_name = " ".join(context.args)
    wine_data[update.effective_user.id] = {"name": wine_name}
    await update.message.reply_text("1. Сколько запечатано на Лобби?")
    return ASK_SEALED_LOBBY

async def ask_sealed_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wine_data[update.effective_user.id]["sealed_lobby"] = parse_int(update.message.text)
    await update.message.reply_text("2. Сколько запечатано на Летнике?")
    return ASK_SEALED_LETNIK

async def ask_sealed_letnik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wine_data[update.effective_user.id]["sealed_letnik"] = parse_int(update.message.text)
    await update.message.reply_text("3. Сколько вскрыто на Лобби?")
    return ASK_OPEN_LOBBY

async def ask_open_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wine_data[update.effective_user.id]["open_lobby"] = parse_int(update.message.text)
    await update.message.reply_text("4. Сколько вскрыто на Летнике?")
    return ASK_OPEN_LETNIK

async def ask_open_letnik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wine_data[update.effective_user.id]["open_letnik"] = parse_int(update.message.text)
    await update.message.reply_text("5. Загрузите фото или напишите '-'")
    return ASK_PHOTO

async def ask_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_data = None
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_data = await photo_file.download_as_bytearray()

    wine = wine_data.get(user_id, {})
    cur.execute('''INSERT INTO wines (name, sealed_lobby, sealed_letnik, open_lobby, open_letnik, photo)
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                (wine["name"], wine["sealed_lobby"], wine["sealed_letnik"],
                 wine["open_lobby"], wine["open_letnik"], photo_data))
    conn.commit()
    await update.message.reply_text("Вино добавлено!")
    wine_data.pop(user_id, None)
    return ConversationHandler.END

#Команда update
def find_closest_wine(name_input):
    cur.execute("SELECT name FROM wines")
    wines = cur.fetchall()
    name_input = name_input.lower()
    matches = [(wine[0], len(os.path.commonprefix([wine[0].lower(), name_input]))) for wine in wines]
    matches = sorted(matches, key=lambda x: x[1], reverse=True)
    return matches[0][0] if matches and matches[0][1] > 0 else None


async def update_wine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пример: /update мерло")
        return ConversationHandler.END

    name_input = " ".join(context.args)
    found = find_closest_wine(name_input)

    if not found:
        await update.message.reply_text("Вино не найдено.")
        return ConversationHandler.END

    update_state[update.effective_user.id] = {"name": found}
    await update.message.reply_text(f"Ведётся изменение вина: {found}.\n1. Сколько запечатано на Лобби? (или 'скип')")
    return ASK_UPDATE_SEALED_LOBBY

async def ask_update_sealed_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() != "скип":
        update_state[update.effective_user.id]["sealed_lobby"] = parse_int(txt)
    await update.message.reply_text("2. Сколько запечатано на Летнике? (или 'скип')")
    return ASK_UPDATE_SEALED_LETNIK

async def ask_update_sealed_letnik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() != "скип":
        update_state[update.effective_user.id]["sealed_letnik"] = parse_int(txt)
    await update.message.reply_text("3. Сколько вскрыто на Лобби? (или 'скип')")
    return ASK_UPDATE_OPEN_LOBBY

async def ask_update_open_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() != "скип":
        update_state[update.effective_user.id]["open_lobby"] = parse_int(txt)
    await update.message.reply_text("4. Сколько вскрыто на Летнике? (или 'скип')")
    return ASK_UPDATE_OPEN_LETNIK

async def ask_update_open_letnik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt.lower() != "скип":
        update_state[update.effective_user.id]["open_letnik"] = parse_int(txt)
    await update.message.reply_text("5. Загрузите новое фото или напишите 'скип'")
    return ASK_UPDATE_PHOTO

async def ask_update_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wine = update_state.get(user_id, {})
    updates = []
    values = []

    if "sealed_lobby" in wine:
        updates.append("sealed_lobby = %s")
        values.append(wine["sealed_lobby"])
    if "sealed_letnik" in wine:
        updates.append("sealed_letnik = %s")
        values.append(wine["sealed_letnik"])
    if "open_lobby" in wine:
        updates.append("open_lobby = %s")
        values.append(wine["open_lobby"])
    if "open_letnik" in wine:
        updates.append("open_letnik = %s")
        values.append(wine["open_letnik"])
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_data = await photo_file.download_as_bytearray()
        updates.append("photo = %s")
        values.append(photo_data)

    if updates:
        query = f"UPDATE wines SET {', '.join(updates)} WHERE name = %s"
        values.append(wine["name"])
        cur.execute(query, tuple(values))
        conn.commit()
        await update.message.reply_text("Информация о вине обновлена.")
    else:
        await update.message.reply_text("Изменения не внесены.")
    
    update_state.pop(user_id, None)
    return ConversationHandler.END


# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wine_data.pop(update.effective_user.id, None)
    await update.message.reply_text("Добавление отменено.")
    return ConversationHandler.END

# Парсер чисел
def parse_int(text):
    return int(text) if text.isdigit() else 0

# Запуск бота
if __name__ == "__main__":
    token = os.environ["BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add)],
        states={
            ASK_SEALED_LOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_sealed_lobby)],
            ASK_SEALED_LETNIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_sealed_letnik)],
            ASK_OPEN_LOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_open_lobby)],
            ASK_OPEN_LETNIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_open_letnik)],
            ASK_PHOTO: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, ask_photo)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    update_conv = ConversationHandler(
    entry_points=[CommandHandler("update", update_wine)],
    states={
        ASK_UPDATE_SEALED_LOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_update_sealed_lobby)],
        ASK_UPDATE_SEALED_LETNIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_update_sealed_letnik)],
        ASK_UPDATE_OPEN_LOBBY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_update_open_lobby)],
        ASK_UPDATE_OPEN_LETNIK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_update_open_letnik)],
        ASK_UPDATE_PHOTO: [MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, ask_update_photo)],
    },
    fallbacks=[CommandHandler("cancel", cancel)]
    )


    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_wines))
    app.add_handler(conv_handler)
    app.add_handler(update_conv)


    logging.info("Bot started...")
    app.run_polling()
