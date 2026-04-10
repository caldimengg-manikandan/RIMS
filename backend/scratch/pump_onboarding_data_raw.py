import psycopg2
import sys
import os
import uuid
import secrets
from datetime import datetime, timezone

# Add backend to path to get settings
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.core.config import get_settings

def pump_data_raw():
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    email = "aashifanshaf786@gmail.com"
    names = [
        "Aarav Sharma", "Ishaan Kapoor", "Sanya Malhotra", "Rohan Verma", 
        "Meera Nair", "Arjun Reddy", "Ananya Gupta", "Vikram Singh", 
        "Zara Khan", "Kabir Das"
    ]

    try:
        # 0. Get an existing HR ID to satisfy NOT NULL constraints
        cursor.execute("SELECT id FROM users WHERE role IN ('hr', 'super_admin') LIMIT 1")
        hr_row = cursor.fetchone()
        hr_id = hr_row[0] if hr_row else None

        # 1. Ensure 10 jobs exist
        job_ids = []
        for i in range(10):
            job_key = f"TEST-JOB-{i+1}"
            cursor.execute("SELECT id FROM jobs WHERE job_id = %s", (job_key,))
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "INSERT INTO jobs (job_id, title, description, domain, status, experience_level, location, mode_of_work, job_type, duration_minutes, hr_id) "
                    "VALUES (%s, %s, 'Sample description for testing.', 'Engineering', 'open', 'mid', 'Remote', 'Remote', 'Full-Time', 60, %s) RETURNING id",
                    (job_key, f"Sample Role {i+1}", hr_id)
                )
                job_internal_id = cursor.fetchone()[0]
            else:
                job_internal_id = row[0]
            job_ids.append(job_internal_id)

        # 2. Pump Applications
        print(f"Pumping 10 applications for {email}...")
        for i, name in enumerate(names):
            job_id = job_ids[i]
            # Check if exists
            cursor.execute("SELECT id FROM applications WHERE job_id = %s AND candidate_email = %s", (job_id, email))
            if cursor.fetchone():
                print(f"Skipping {name} (already exists)")
                continue

            token = str(uuid.uuid4())
            short_id = secrets.token_urlsafe(8)
            cursor.execute(
                "INSERT INTO applications (job_id, candidate_name, candidate_email, candidate_phone, status, offer_sent, offer_token, offer_short_id, offer_approval_status, onboarding_approval_status) "
                "VALUES (%s, %s, %s, '9876543210', 'hired', false, %s, %s, 'none', 'pending')",
                (job_id, name, email, token, short_id)
            )
        
        conn.commit()
        print("Success: 10 applications created via Raw SQL.")
    except Exception as e:
        print(f"Raw SQL Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    pump_data_raw()
