import psycopg2
import sys
import os
import uuid
import secrets

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.core.config import get_settings

def pump_data_same_job():
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    # Target Job and Email
    target_job_id = "JOB-877X5D"
    base_email = "aashifanshaf786@gmail.com"
    
    names = [
        "Aarav Sharma", "Ishaan Kapoor", "Sanya Malhotra", "Rohan Verma", 
        "Meera Nair", "Arjun Reddy", "Ananya Gupta", "Vikram Singh", 
        "Zara Khan", "Kabir Das"
    ]

    try:
        # 0. Get HR ID
        cursor.execute("SELECT id FROM users WHERE role IN ('hr', 'super_admin') LIMIT 1")
        hr_row = cursor.fetchone()
        hr_id = hr_row[0] if hr_row else None

        # 1. Ensure the specific job exists
        cursor.execute("SELECT id FROM jobs WHERE job_id = %s", (target_job_id,))
        row = cursor.fetchone()
        if not row:
            print(f"Job {target_job_id} not found. Creating it...")
            cursor.execute(
                "INSERT INTO jobs (job_id, title, description, domain, status, experience_level, location, mode_of_work, job_type, duration_minutes, hr_id) "
                "VALUES (%s, %s, 'Software Developer role for testing.', 'Engineering', 'open', 'mid', 'Remote', 'Remote', 'Full-Time', 60, %s) RETURNING id",
                (target_job_id, "Software Developer", hr_id)
            )
            job_internal_id = cursor.fetchone()[0]
        else:
            job_internal_id = row[0]

        print(f"Pumping 10 applications for job {target_job_id}...")

        for i, name in enumerate(names):
            # Use Gmail dots to satisfy unique constraint (job_id, email)
            # aashifanshaf786@gmail.com, a.ashifanshaf786@gmail.com, etc.
            username, domain = base_email.split('@')
            if i == 0:
                email = base_email
            else:
                # Insert a dot at index i
                pos = min(i, len(username) - 1)
                email = username[:pos] + '.' + username[pos:] + '@' + domain
            
            token = str(uuid.uuid4())
            short_id = secrets.token_urlsafe(8)
            
            # Check if exists
            cursor.execute("SELECT id FROM applications WHERE job_id = %s AND candidate_email = %s", (job_internal_id, email))
            if cursor.fetchone():
                print(f"Skipping {name} (already exists)")
                continue

            cursor.execute(
                "INSERT INTO applications (job_id, candidate_name, candidate_email, candidate_phone, status, offer_sent, offer_token, offer_short_id, offer_approval_status, onboarding_approval_status, hr_id) "
                "VALUES (%s, %s, %s, '9876543210', 'hired', false, %s, %s, 'none', 'pending', %s)",
                (job_internal_id, name, email, token, short_id, hr_id)
            )
        
        conn.commit()
        print(f"Success: 10 applications created under job {target_job_id}.")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    pump_data_same_job()
