import psycopg2
import sys
import os
import uuid
import secrets
import argparse
from datetime import datetime, timezone, timedelta

# Add the parent of the 'app' directory to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
# The 'app' folder is inside 'backend', and scripts is also inside 'backend'
# Let's get the absolute path to the 'backend' folder
backend_dir = os.path.dirname(script_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)
from app.core.config import get_settings

def inject_candidate(name, email, job_code, stage):
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    cursor = conn.cursor()
    
    try:
        # 1. Get Job ID
        cursor.execute("SELECT id FROM jobs WHERE job_id = %s", (job_code,))
        row = cursor.fetchone()
        if not row:
            print(f"Error: Job {job_code} not found.")
            return
        job_id = row[0]

        # 2. Get HR ID (owner of the job)
        cursor.execute("SELECT hr_id FROM jobs WHERE id = %s", (job_id,))
        hr_id = cursor.fetchone()[0]

        # 3. Generate tokens (required for offer/onboarding stages)
        offer_token = str(uuid.uuid4())
        short_id = secrets.token_urlsafe(8)
        
        # 4. Prepare data
        # Mapping some fields based on stage
        is_offer_sent = stage in ['offer_sent', 'accepted', 'rejected', 'onboarded']
        onboarding_status = 'pending' if stage in ['hired', 'pending_approval'] else 'none'
        if stage == 'onboarded': onboarding_status = 'completed'
        
        print(f"Injecting {name} ({email}) into stage: {stage}...")

        cursor.execute(
            """
            INSERT INTO applications (
                job_id, hr_id, candidate_name, candidate_email, candidate_phone, 
                status, offer_sent, offer_token, offer_short_id, 
                offer_token_expiry, joining_date, onboarding_approval_status
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id
            """,
            (
                job_id, hr_id, name, email, '+91 9876543210', 
                stage, is_offer_sent, offer_token, short_id,
                datetime.now(timezone.utc) + timedelta(days=7),
                datetime.now() + timedelta(days=30),
                onboarding_status
            )
        )
        
        app_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"Successfully injected App ID: {app_id}")
        print(f"Direct Response Link: http://localhost:3000/offer/respond?token={offer_token}")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject a single candidate into a specific stage.")
    parser.add_argument("--name", default="Test Candidate", help="Candidate Name")
    parser.add_argument("--email", default="test@example.com", help="Candidate Email")
    parser.add_argument("--job", default="JOB-877X5D", help="Internal Job Code (e.g. JOB-877X5D)")
    parser.add_argument("--stage", default="hired", choices=[
        'applied', 'screened', 'aptitude_round', 'ai_interview', 
        'hired', 'pending_approval', 'offer_sent', 'accepted', 'onboarded'
    ], help="Target Status/Stage")

    args = parser.parse_args()
    inject_candidate(args.name, args.email, args.job, args.stage)
