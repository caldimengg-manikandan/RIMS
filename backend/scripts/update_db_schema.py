import sqlite3
import os

def update_schema():
    # Ensure we look in the current directory or backend directory
    db_path = 'sql_app.db'
    if not os.path.exists(db_path):
        # Try backend/sql_app.db if running from root
        if os.path.exists(os.path.join('backend', db_path)):
            db_path = os.path.join('backend', db_path)
        else:
            print(f"Database not found at {db_path}")
            # Try to find it
            for root, dirs, files in os.walk('.'):
                if 'sql_app.db' in files:
                    db_path = os.path.join(root, 'sql_app.db')
                    print(f"Found database at {db_path}")
                    break
    
    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Checking schema...")
        cursor.execute("PRAGMA table_info(interviews)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        if 'locked_skill' not in columns:
            print("Attempting to add locked_skill column...")
            cursor.execute("ALTER TABLE interviews ADD COLUMN locked_skill VARCHAR(50)")
            conn.commit()
            print("Success: locked_skill column added.")
        else:
            print("Info: locked_skill column already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_schema()
