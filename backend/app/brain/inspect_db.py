import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, full_name, role FROM users LIMIT 10"))
    for row in result:
        print(f"ID: {row[0]}, Name: {row[1]}, Role: '{row[2]}'")
