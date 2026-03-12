import sqlite3
import os

db_path = "../sql_app.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, full_name, role, is_active, is_verified FROM users;")
        rows = cursor.fetchall()
        print("Users found in ROOT DB:")
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error reading root DB: {e}")
    conn.close()
else:
    print(f"{db_path} not found")
