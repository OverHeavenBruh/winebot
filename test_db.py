import psycopg2

# Данные для подключения
conn = psycopg2.connect(
    host="postgres.railway.internal",
    database="railway",
    user="postgres",
    password="DGNrIfgnoTsFqYzCwyCTSMGAwzxGIBUL",
    port=5432
)

cur = conn.cursor()

# Создание таблицы, если нет
cur.execute('''
    CREATE TABLE IF NOT EXISTS wines (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL
    );
''')
conn.commit()

# Тестовая вставка
cur.execute("INSERT INTO wines (name, quantity) VALUES (%s, %s)", ("Тестовое Вино", 3))
conn.commit()

# Вывод всех вин
cur.execute("SELECT name, quantity FROM wines ORDER BY name")
rows = cur.fetchall()
print("🟣 Список вин в базе:")
for row in rows:
    print(f"— {row[0]}: {row[1]} шт.")

cur.close()
conn.close()

