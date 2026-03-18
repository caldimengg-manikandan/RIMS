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

alter_queries = [
    "ALTER TABLE jobs ADD COLUMN duration_minutes INT DEFAULT 60",
]

try:
    with engine.connect() as connection:
        for query in alter_queries:
            try:
                connection.execute(text(query))
                print(f"Executed: {query}")
            except Exception as e:
                print(f"Query '{query}' failed/skipped: {e}")
        connection.commit()
    print("Job finished!")
except Exception as e:
    print(f"Failed to execute modifications: {e}")
