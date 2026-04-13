import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def check_rls_policies():
    with engine.connect() as conn:
        print("--- Checking RLS Policies ---")
        query = text("""
            SELECT tablename, policyname, permissive, roles, cmd, qual, with_check 
            FROM pg_policies
        """)
        try:
            res = conn.execute(query)
            policies = [dict(r._mapping) for r in res]
            print(f"Found {len(policies)} RLS policies")
            for p in policies:
                print(p)
        except Exception as e:
            print(f"Error checking RLS (maybe not on Postgres or not enough permissions): {e}")

        print("\n--- Checking Table RLS Status ---")
        query = text("""
            SELECT schemaname, tablename, rowsecurity 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        try:
            res = conn.execute(query)
            tables = [dict(r._mapping) for r in res]
            for t in tables:
                print(f"Table: {t['tablename']}, RLS Enabled: {t['rowsecurity']}")
        except Exception as e:
            print(f"Error checking table RLS: {e}")

if __name__ == "__main__":
    check_rls_policies()
