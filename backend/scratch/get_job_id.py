from sqlalchemy import create_engine, text
import os

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/rims"

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT id, title FROM jobs WHERE status = 'open' LIMIT 1;"))
    row = result.fetchone()
    if row:
        print(f"ID: {row[0]}, Title: {row[1]}")
    else:
        print("No open jobs found.")
