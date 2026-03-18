import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("DATABASE_URL not found in .env")
    exit(1)

if not db_url.startswith("mysql"):
    print("DATABASE_URL is not MySQL. Skipping DB creation.")
    exit(0)

# Parse URL to get base connection without database name
# Typical URL: mysql+pymysql://root:password@localhost:3306/rims_db
try:
    base_url, db_name = db_url.rsplit("/", 1)
    if not db_name:
         raise ValueError("Invalid database string")
except ValueError:
    print("Invalid DATABASE_URL format. Must be mysql+pymysql://user:pass@host/dbname")
    exit(1)

print(f"Connecting to MySQL server at {base_url}...")
# Create engine connected to server, not database
engine = create_engine(base_url, pool_pre_ping=True)

try:
    with engine.connect() as connection:
        # Create database
        connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        print(f"Successfully created or verified database: {db_name}")

except Exception as e:
    print(f"Failed to create database: {e}")
    exit(1)
