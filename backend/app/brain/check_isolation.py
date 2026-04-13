import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

def check_isolation_health():
    with engine.connect() as conn:
        print("--- Checking Applications vs Jobs hr_id mismatch ---")
        query = text("""
            SELECT a.id as app_id, a.job_id, a.hr_id as app_hr, j.hr_id as job_hr 
            FROM applications a 
            JOIN jobs j ON a.job_id = j.id 
            WHERE a.hr_id != j.hr_id OR a.hr_id IS NULL
        """)
        res = conn.execute(query)
        mismatches = [dict(r._mapping) for r in res]
        print(f"Found {len(mismatches)} applications with missing or mismatched hr_id")
        for m in mismatches[:10]:
            print(m)

        print("\n--- Checking Jobs with NULL hr_id ---")
        query = text("SELECT id, title FROM jobs WHERE hr_id IS NULL")
        res = conn.execute(query)
        orphaned_jobs = [dict(r._mapping) for r in res]
        print(f"Found {len(orphaned_jobs)} jobs with NULL hr_id")
        for j in orphaned_jobs[:10]:
            print(j)

        print("\n--- Checking Users and Roles ---")
        query = text("SELECT id, email, role FROM users")
        res = conn.execute(query)
        users = [dict(r._mapping) for r in res]
        for u in users:
            print(u)

if __name__ == "__main__":
    check_isolation_health()
