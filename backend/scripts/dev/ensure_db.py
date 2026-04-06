import os
import sys
from dotenv import load_dotenv

# Load env from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

def create_database():
    """
    PostgreSQL databases must be created via psql or a DB admin tool.
    This script verifies that the DATABASE_URL env var is set correctly
    and that a connection to PostgreSQL can be established.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env. Cannot verify database.")
        sys.exit(1)

    if not db_url.startswith("postgresql"):
        print(f"WARNING: DATABASE_URL does not appear to be PostgreSQL: {db_url[:40]}...")

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"Successfully connected to PostgreSQL database: '{db_name}'")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_database()
