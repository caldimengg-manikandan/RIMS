import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def check_db_user():
    with engine.connect() as conn:
        print("--- Checking Database User ---")
        try:
            res = conn.execute(text("SELECT current_user, session_user"))
            print(f"Users: {dict(res.first()._mapping)}")
            
            res = conn.execute(text("SELECT usename, usesuper, usecreatedb FROM pg_user WHERE usename = current_user"))
            print(f"Privileges: {dict(res.first()._mapping)}")
            
            res = conn.execute(text("SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'jobs'"))
            print(f"RLS Status for 'jobs': {dict(res.first()._mapping)}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_db_user()
