from sqlalchemy import create_engine
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.infrastructure.database import SessionLocal
from app.domain.models import Application, Job, User
import uuid
import secrets

def pump_data():
    db = SessionLocal()
    try:
        from app.domain import models 
        
        email = "aashifanshaf786@gmail.com"
        
        # 1. Create 10 dummy jobs to satisfy unique constraint (job_id, email)
        jobs = []
        for i in range(10):
            job_id = f"TEST-JOB-{i+1}"
            # Check if exists
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                job = Job(
                    job_id=job_id,
                    title=f"Sample Role {i+1}",
                    domain="Engineering",
                    status="open",
                    experience_level="mid"
                )
                db.add(job)
                db.flush()
            jobs.append(job)

        # 2. Get an HR
        hr = db.query(User).filter(User.role == 'hr').first()
        if not hr:
            hr = db.query(User).filter(User.role == 'super_admin').first()
            
        names = [
            "Aarav Sharma", "Ishaan Kapoor", "Sanya Malhotra", "Rohan Verma", 
            "Meera Nair", "Arjun Reddy", "Ananya Gupta", "Vikram Singh", 
            "Zara Khan", "Kabir Das"
        ]

        print(f"Pumping 10 applications for {email} into 10 different jobs...")

        for i, name in enumerate(names):
            job = jobs[i]
            # Check if exists
            exists = db.query(Application).filter(Application.job_id == job.id, Application.candidate_email == email).first()
            if exists: 
                print(f"Skipping {name} (already exists for {job.job_id})")
                continue

            app = Application(
                candidate_name=name,
                candidate_email=email,
                candidate_phone="9876543210",
                job_id=job.id,
                hr_id=hr.id if hr else None,
                status='hired',
                offer_sent=False,
                offer_approval_status='none',
                offer_token=str(uuid.uuid4()),
                offer_short_id=secrets.token_urlsafe(8)
            )
            db.add(app)
        
        db.commit()
        print("Success: 10 applications created across 10 jobs.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    pump_data()
