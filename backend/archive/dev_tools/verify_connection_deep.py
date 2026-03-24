import os
import sys
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, extract, cast, Date, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from pathlib import Path

# Load env from backend/.env
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

load_dotenv(backend_dir / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

async def deep_validation():
    print("--- STARTING DEEP END-TO-END VALIDATION ---")
    print(f"Connecting to: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
    
    from app.domain.models import Application, Job, ResumeExtraction, User
    
    try:
        # 1. Verify Job exists or create dummy
        job = db.query(Job).first()
        if not job:
            print("No jobs found, creating dummy 'Software Engineer' job...")
            # We need an HR user for the FK
            hr = db.query(User).filter(User.role == "hr").first()
            if not hr:
                hr = db.query(User).first()
            if not hr:
                print("No HR users found either. Cannot create dummy job. Aborting.")
                return
            
            job = Job(
                title="Validation Test Engineer",
                description="Testing deep end-to-end setups on PostgreSQL",
                experience_level="Mid",
                hr_id=hr.id,
                status="open"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            print(f"Created Job ID: {job.id}")

        # 2. Simulate Application Creation (INSERT Trace)
        test_email = f"val_test_{int(datetime.now().timestamp())}@example.com"
        print(f"\n[1/4] Simulating Apply: email={test_email}")
        app = Application(
            job_id=job.id,
            candidate_name="Validation Candidate",
            candidate_email=test_email,
            candidate_phone="9988776655",
            resume_file_path="uploads/resumes/dummy.pdf",
            status="applied"
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        print(f"-> SUCCESS: Created Application ID: {app.id}")

        # 3. Simulate Extraction Store (INSERT/UPSERT Trace)
        print(f"\n[2/4] Simulating ResumeExtraction creation for App {app.id}")
        re = ResumeExtraction(
            application_id=app.id,
            extracted_text="Skills: Python, SQLAlchemy, Docker, Postgres",
            summary="Strong backend engineer",
            extracted_skills='["Python", "SQLAlchemy", "Postgres"]',
            resume_score=8.5
        )
        db.add(re)
        db.commit()
        print("-> SUCCESS: Saved ResumeExtraction")

        # 4. Filter Validation: Time of Day (ADDRESSING TIMEZONES)
        print("\n[3/4] Validating Time Range Filters with UTC Offset Accuracy")
        hour_expr_raw = extract('hour', Application.applied_at)
        hour_expr_tz = extract('hour', text("(\"applications\".\"applied_at\" AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Kolkata'"))
        
        app_list_raw = db.query(Application).filter(Application.id == app.id).filter(hour_expr_raw.between(0, 24)).all()
        print(f" Raw Count (0-24): {len(app_list_raw)}")
        
        # Test offset exact match
        curr_hour_approx = datetime.now().hour # usually local evening/night
        print(f" Current Local Hour (approx): {curr_hour_approx}")
        
        try:
             app_list_tz = db.query(Application).filter(Application.id == app.id).filter(hour_expr_tz == curr_hour_approx).all()
             print(f" Timezone-Aware Match: {len(app_list_tz) > 0} (Might fail if trigger timings offset by seconds)")
        except Exception as filter_e:
             print(f" Timezone filtering error directly with text construct: {filter_e}")

        # 5. Retrieval Check (GET Trace with Joins)
        print(f"\n[4/4] Verifying Relationship Loading (Joins)")
        fetched = db.query(Application).filter(Application.id == app.id).first()
        if fetched:
             print(f" Candidate: {fetched.candidate_name}")
             print(f" Job: {fetched.job.title if fetched.job else 'MISSING'}")
             print(f" Extraction Summary: {fetched.resume_extraction.summary if fetched.resume_extraction else 'MISSING'}")
             if fetched.resume_extraction:
                  print(" -> Full flow connected successfully.")
        else:
             print(" FAILED to retrieve application that was just inserted.")

    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Verification crashed: {e}")
        db.rollback()
    finally:
        # Cleanup test app so we don't pollute DB
        try:
            db.query(Application).filter(Application.candidate_email.like("val_test_%_@example.com")).delete(synchronize_session=False)
            db.commit()
            print("\nCleanup completed.")
        except:
             pass
        db.close()

if __name__ == "__main__":
    asyncio.run(deep_validation())
