import os
import logging
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print(f"Testing migrations with: {db_url.split('@')[-1]}")

def column_exists(conn, table_name: str, column_name: str) -> bool:
    inspector = inspect(conn)
    if table_name not in inspector.get_table_names():
        return False
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns

_REQUIRED_COLUMNS = [
    ("jobs", "aptitude_questions_file", "VARCHAR(500)"),
    ("applications", "resume_file_path", "VARCHAR(500)"),
]

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Connected.")
        for table, column, col_type in _REQUIRED_COLUMNS:
            print(f"Checking {table}.{column}...")
            if not column_exists(conn, table, column):
                print(f"Adding column {table}.{column}...")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"))
                conn.commit()
                print("Done.")
            else:
                print("Exists.")
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
