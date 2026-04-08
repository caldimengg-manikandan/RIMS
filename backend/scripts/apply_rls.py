from app.infrastructure.database import engine
from sqlalchemy import text
import logging

def apply_rls():
    with open('scripts/rls_hardening.sql', 'r') as f:
        sql = f.read()
    
    with engine.connect() as conn:
        with conn.begin():
            for stmt in sql.split(';'):
                if stmt.strip():
                    conn.execute(text(stmt))
        print("RLS Hardening Applied.")

if __name__ == "__main__":
    apply_rls()
