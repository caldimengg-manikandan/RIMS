import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print(f"Testing connection to: {db_url.split('@')[-1]}")

try:
    conn = psycopg2.connect(db_url)
    print("Connection successful!")
    cur = conn.cursor()
    cur.execute("SELECT email, role, is_active, is_verified, approval_status FROM users WHERE email = %s", ("caldiminternship@gmail.com",))
    user = cur.fetchone()
    if user:
        print(f"User found: {user}")
    else:
        print("User not found.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
