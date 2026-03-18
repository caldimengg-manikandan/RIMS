import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("DATABASE_URL not found")
    exit(1)

print(f"Connecting to: {db_url}")
engine = create_engine(db_url)

try:
    with engine.connect() as connection:
        # Get tables
        tables_query = connection.execute(text("SHOW TABLES"))
        tables = [row[0] for row in tables_query]
        
        print("\nTable Row Counts:")
        for table in tables:
            count_query = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_query.scalar()
            print(f" - {table}: {count} rows")

except Exception as e:
    print(f"Failed to inspect: {e}")
