import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
print(f"Checking for locks on: {db_url.split('@')[-1]}")

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("""
        SELECT pid, usename, pg_blocking_pids(pid) as blocked_by, query 
        FROM pg_stat_activity 
        WHERE state = 'active' AND pid != pg_backend_pid();
    """)
    rows = cur.fetchall()
    if rows:
        print("Active queries:")
        for row in rows:
            print(row)
    else:
        print("No active queries found.")
    
    cur.execute("""
        SELECT
            blocked_locks.pid AS blocked_pid,
            blocking_locks.pid AS blocking_pid,
            blocked_activity.query AS blocked_statement,
            blocking_activity.query AS blocking_statement
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_locks.pid = blocked_activity.pid
        JOIN pg_catalog.pg_locks blocking_locks 
            ON blocking_locks.locktype = blocked_locks.locktype
            AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
            AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
            AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
            AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
            AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
            AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
            AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
            AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
            AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
            AND blocking_locks.pid != blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_locks.pid = blocking_activity.pid
        WHERE NOT blocked_locks.GRANTED;
    """)
    rows = cur.fetchall()
    if rows:
        print("Lock conflicts:")
        for row in rows:
            print(row)
    else:
        print("No lock conflicts found.")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
