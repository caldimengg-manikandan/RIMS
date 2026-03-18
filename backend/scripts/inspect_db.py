import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("DATABASE_URL not found")
    exit(1)

print(f"Connecting to: {db_url}")
engine = create_engine(db_url)
inspector = inspect(engine)

try:
    tables = inspector.get_table_names()
    print("\nColumns in tables:")
    for table in tables:
        print(f"\n--- {table} ---")
        columns = inspector.get_columns(table)
        for col in columns:
            print(f" - {col['name']} ({col['type']})")

except Exception as e:
    print(f"Failed to inspect: {e}")
