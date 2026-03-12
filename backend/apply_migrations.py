import sqlite3
import os

db_path = 'C:/R/RIMS/backend/sql_app.db'

def update_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Checking/Adding duration_minutes to jobs table...")
        cursor.execute("ALTER TABLE jobs ADD COLUMN duration_minutes INTEGER DEFAULT 60")
        print("Column added to jobs table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column already exists in jobs table.")
        else:
            print(f"Error updating jobs table: {e}")

    try:
        print("Checking/Adding duration_minutes to interviews table...")
        cursor.execute("ALTER TABLE interviews ADD COLUMN duration_minutes INTEGER DEFAULT 60")
        print("Column added to interviews table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column already exists in interviews table.")
        else:
            print(f"Error updating interviews table: {e}")

    conn.commit()
    conn.close()
    print("Database update complete.")

if __name__ == "__main__":
    update_db()
