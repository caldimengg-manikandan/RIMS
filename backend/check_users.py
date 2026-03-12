import sqlite3
import os

db_path = "sql_app.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, full_name, role, is_active, is_verified FROM users;")
    rows = cursor.fetchall()
    print("Users found:")
    for row in rows:
        print(row)
    conn.close()
else:
    print(f"{db_path} not found")
