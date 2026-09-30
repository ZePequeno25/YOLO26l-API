import sqlite3, os, sys

sys.stdout.reconfigure(encoding='utf-8')

db_path = "api-tcc/data/prediction_metrics.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(prediction_metrics)")
columns = cursor.fetchall()
print("Colunas da tabela prediction_metrics:")
for col in columns:
    print(col)

conn.close()
