import os
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
import os

db_url = os.getenv("DATABASE_URL")
print(f"Connecting to {db_url}")

engine = create_engine(db_url)
try:
    with engine.connect() as conn:
        print("SQLAlchemy connected successfully!")
except Exception as e:
    print(f"Failed to connect: {e}")
