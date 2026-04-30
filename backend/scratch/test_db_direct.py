import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Try using the project DB host directly (port 5432)
db_url = "postgresql://postgres.itajqbrebdbrunfqpbmg:Caldim%402026@db.itajqbrebdbrunfqpbmg.supabase.co:5432/postgres?sslmode=require"
print(f"Testing connection to: db.itajqbrebdbrunfqpbmg.supabase.co:5432")

try:
    conn = psycopg2.connect(db_url)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
