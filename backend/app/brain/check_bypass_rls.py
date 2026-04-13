import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def check_bypass_rls():
    with engine.connect() as conn:
        print("--- Checking BYPASSRLS Attribute ---")
        try:
            res = conn.execute(text("SELECT rolname, rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user"))
            row = res.first()
            if row:
                print(f"Role: {row.rolname}, BypassRLS: {row.rolbypassrls}, Superuser: {row.rolsuper}")
                if row.rolbypassrls:
                    print("CRITICAL: The current database user has BYPASSRLS set to True. This overrides ALL RLS policies!")
            else:
                print("Could not find role info.")
        except Exception as e:
            print(f"Error checking bypass: {e}")

if __name__ == "__main__":
    check_bypass_rls()
