import sys
import os
sys.path.append(os.getcwd())

from app.infrastructure.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)

def check():
    with engine.connect() as conn:
        print("--- ACTIVE QUERIES ---")
        try:
            res = conn.execute(text("SELECT pid, query, state, wait_event_type, wait_event FROM pg_stat_activity WHERE state != 'idle' AND pid != pg_backend_pid();")).fetchall()
            for r in res:
                print(r)
        except Exception as e:
            print(f"Error checking activity: {e}")

        print("\n--- TABLES ---")
        try:
            res = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';")).fetchall()
            print([r[0] for r in res])
        except Exception as e:
            print(f"Error checking tables: {e}")

if __name__ == "__main__":
    check()
