import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Try using the IP address directly
db_url = "postgresql://postgres.itajqbrebdbrunfqpbmg:Caldim%402026@3.111.225.200:6543/postgres?sslmode=require"
print(f"Testing connection to IP: 3.111.225.200")

try:
    conn = psycopg2.connect(db_url)
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
