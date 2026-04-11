import psycopg2
import sys
import os
from urllib.parse import urlparse

# DATABASE_URL=postgresql://postgres.itajqbrebdbrunfqpbmg:Caldim%402026@aws-1-ap-south-1.pooler.supabase.com:6543/postgres
db_url = "postgresql://postgres.itajqbrebdbrunfqpbmg:Caldim%402026@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

def test_conn(url):
    print(f"Testing connection to: {urlparse(url).hostname}")
    try:
        conn = psycopg2.connect(url, connect_timeout=10)
        print("CONNECTION SUCCESSFUL!")
        conn.close()
        return True
    except Exception as e:
        print(f"CONNECTION FAILED: {e}")
        return False

if __name__ == "__main__":
    test_conn(db_url)
    
    # Try alternative (direct if pooler is failing)
    # itajqbrebdbrunfqpbmg.supabase.co
    # Note: postgresql port is usually 5432 for direct, 6543 for pooler
    print("\nTrying direct connection host...")
    alt_url = db_url.replace("aws-1-ap-south-1.pooler.supabase.com:6543", "db.itajqbrebdbrunfqpbmg.supabase.co:5432")
    test_conn(alt_url)
