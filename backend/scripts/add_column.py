import sys
import os

# Add the parent directory to sys.path to resolve app imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

def add_column():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN experience_level VARCHAR(50)"))
            print("Column 'experience_level' added successfully.")
        except Exception as e:
            print(f"Error adding column (it might already exist): {e}")

if __name__ == "__main__":
    add_column()
