import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env from the backend folder
_backend_dir = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(_backend_dir, ".env"))

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("DATABASE_URL not found in .env")
    sys.exit(1)

if not db_url.startswith("postgresql"):
    print(f"DATABASE_URL does not appear to be PostgreSQL: {db_url[:40]}...")
    print("This script is for PostgreSQL. Please update DATABASE_URL in your .env file.")
    sys.exit(1)

print(f"Connecting to PostgreSQL at: {db_url.split('@')[-1] if '@' in db_url else db_url}...")

# For PostgreSQL, databases are created via psql or admin tools.
# This script verifies the connection and confirms all required tables exist.
engine = create_engine(db_url, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_database(), version()"))
        db_name, version = result.fetchone()
        print(f"Connected to PostgreSQL database: '{db_name}'")
        print(f"Server version: {version.split(',')[0]}")

        # List all tables in the public schema
        tables_result = connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        )
        tables = [row[0] for row in tables_result]
        if tables:
            print(f"\nExisting tables ({len(tables)}):")
            for t in tables:
                print(f"  - {t}")
        else:
            print("\nNo tables found. Run Alembic migrations or create_tables.py to initialize the schema.")

except Exception as e:
    print(f"Failed to connect to database: {e}")
    sys.exit(1)
