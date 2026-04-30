import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print(f"Testing inspector with: {db_url.split('@')[-1]}")

try:
    engine = create_engine(db_url)
    inspector = inspect(engine)
    print("Getting table names...")
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    if "users" in tables:
        print("Getting columns for 'users'...")
        columns = inspector.get_columns("users")
        print(f"Found {len(columns)} columns.")
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
