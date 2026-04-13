import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def debug_rls_session():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("--- Debugging RLS Session Variables ---")
            
            # 1. Check initially
            res = conn.execute(text("SELECT current_setting('app.current_user_id', true)"))
            print(f"Initial setting: {res.scalar()}")
            
            # 2. Set it
            conn.execute(text("SET LOCAL app.current_user_id = '99'"))
            
            # 3. Check again (should be '99')
            res = conn.execute(text("SELECT current_setting('app.current_user_id', true)"))
            print(f"After SET LOCAL: {res.scalar()}")
            
            # 4. Check if it leaks across connections (should NOT)
            with engine.connect() as conn2:
                res2 = conn2.execute(text("SELECT current_setting('app.current_user_id', true)"))
                print(f"Connection 2 (should be None): {res2.scalar()}")
            
            trans.rollback()
        except Exception as e:
            print(f"Error: {e}")
            trans.rollback()

if __name__ == "__main__":
    debug_rls_session()
