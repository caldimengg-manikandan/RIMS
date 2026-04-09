import sys
import os
sys.path.append(os.getcwd())

from app.infrastructure.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("--- INTERVIEWS COLUMNS ---")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'interviews'")).fetchall()
    cols = [r[0] for r in res]
    print(cols)
    print("current_difficulty" in cols)

    print("\n--- APPLICATIONS COLUMNS ---")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'applications'")).fetchall()
    cols = [r[0] for r in res]
    print(cols)
    print("resume_score" in cols)
