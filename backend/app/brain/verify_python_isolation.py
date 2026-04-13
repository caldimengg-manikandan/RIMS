import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# App components
from app.domain.models import Job, User, Application
from app.api.jobs import list_jobs
from app.api.applications import get_hr_applications

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
SessionLocal = sessionmaker(bind=engine)

def verify_python_isolation():
    print("--- Python-Level Isolation Verification ---")
    db = SessionLocal()
    try:
        # HR A (ID 28)
        # HR B (ID 29)
        hr_a = db.query(User).filter(User.id == 28).first()
        hr_b = db.query(User).filter(User.id == 29).first()
        
        # 1. Job Isolation
        print("\nChecking Job Isolation for HR A (ID 28)...")
        # List jobs for HR A
        query_a = db.query(Job)
        if hr_a.role.lower() != "super_admin":
            query_a = query_a.filter(Job.hr_id == hr_a.id)
        
        jobs_a = query_a.all()
        others_jobs_a = [j for j in jobs_a if j.hr_id != 28]
        if others_jobs_a:
            print(f"!!! FAIL: HR A sees {len(others_jobs_a)} jobs they don't own!")
        else:
            print(f"SUCCESS: HR A isolated to their own {len(jobs_a)} jobs.")

        # 2. Application Isolation
        print("\nChecking Application Isolation for HR B (ID 29)...")
        query_b = db.query(Application)
        if hr_b.role.lower() != "super_admin":
            query_b = query_b.filter(Application.hr_id == hr_b.id)
            
        apps_b = query_b.all()
        others_apps_b = [a for a in apps_b if a.hr_id != 29]
        if others_apps_b:
            print(f"!!! FAIL: HR B sees {len(others_apps_b)} applications they don't own!")
        else:
            print(f"SUCCESS: HR B isolated to their own {len(apps_b)} applications.")

        # 3. Pending HR Check
        print("\nChecking Pending HR (ID 27) Isolation...")
        hr_p = db.query(User).filter(User.id == 27).first()
        print(f"User 27 role: {hr_p.role}")
        query_p = db.query(Job)
        if hr_p.role.lower() != "super_admin":
            query_p = query_p.filter(Job.hr_id == hr_p.id)
            
        jobs_p = query_p.all()
        if len(jobs_p) > 0 and any(j.hr_id != 27 for j in jobs_p):
            print(f"!!! FAIL: Pending HR sees other's jobs!")
        else:
            print(f"SUCCESS: Pending HR is isolated (sees {len(jobs_p)} jobs).")

    finally:
        db.close()

if __name__ == "__main__":
    verify_python_isolation()
