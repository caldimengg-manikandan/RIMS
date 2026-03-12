import sqlite3
import os

# SQLite Runtime Performance Tuning Script
# No source code modification required.

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "sql_app.db")

def optimize_db():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    print(f"⚙️ Tuning SQLite settings for: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Enable WAL mode for concurrent reads/writes
        cursor.execute("PRAGMA journal_mode = WAL;")
        
        # 2. Set synchronous to NORMAL for faster writes without risking severe corruption
        cursor.execute("PRAGMA synchronous = NORMAL;")
        
        # 3. Increase page cache to 64MB (-64000 KB)
        cursor.execute("PRAGMA cache_size = -64000;")
        
        # 4. Use memory for temporary storage
        cursor.execute("PRAGMA temp_store = MEMORY;")
        
        # 5. Optimize the database
        cursor.execute("PRAGMA optimize;")

        conn.commit()
        
        # Verify settings
        cursor.execute("PRAGMA journal_mode;")
        jm = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA cache_size;")
        cs = cursor.fetchone()[0]
        
        print(f"✅ Optimization complete!")
        print(f"📊 Journal Mode: {jm}")
        print(f"📊 Cache Size: {abs(cs // 1024)}MB")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error optimizing database: {e}")

if __name__ == "__main__":
    optimize_db()
