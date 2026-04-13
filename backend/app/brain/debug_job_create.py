import os
import json
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Mock app components
from app.domain.models import User, Job
from app.domain.schemas import JobCreate
from app.infrastructure.database import Base

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def test_create_job():
    try:
        # Find an HR user
        hr = db.query(User).filter(User.role == 'hr').first()
        if not hr:
            print("No HR user found")
            return

        print(f"Testing with HR: {hr.email} (ID: {hr.id})")

        # Mock JobCreate data
        job_data = JobCreate(
            title="Intern Test Job " + uuid.uuid4().hex[:6],
            description="Detailed job description for testing purposes.",
            experience_level="intern",
            aptitude_enabled=True,
            aptitude_mode="ai",
            domain="Engineering",
            primary_evaluated_skills=["Python", "SQL"]
        )

        # ── Logic from api/jobs.py ──
        from app.api.jobs import _validate_job_content, _validate_interview_pipeline, generate_unique_job_id
        
        _validate_job_content(job_data.title, job_data.description, db)
        pipeline = _validate_interview_pipeline(job_data, job_data.experience_level)
        job_identifier = generate_unique_job_id(db)

        new_job = Job(
            job_id=job_identifier,
            interview_token=uuid.uuid4().hex,
            title=job_data.title,
            description=job_data.description,
            experience_level=job_data.experience_level,
            hr_id=hr.id,
            location=job_data.location,
            mode_of_work=job_data.mode_of_work,
            job_type=job_data.job_type,
            domain=job_data.domain,
            primary_evaluated_skills=json.dumps(job_data.primary_evaluated_skills),
            aptitude_enabled=pipeline["aptitude_enabled"],
            first_level_enabled=pipeline["first_level_enabled"],
            interview_mode=pipeline["interview_mode"],
            behavioral_role=pipeline["behavioral_role"] or "general",
            uploaded_question_file=pipeline["uploaded_question_file"],
            duration_minutes=pipeline["duration_minutes"],
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        print(f"Job created successfully: {new_job.id} ({new_job.job_id})")

        # Test Audit Log
        from app.services.candidate_service import CandidateService
        cand_service = CandidateService(db)
        cand_service.create_audit_log(hr.id, "JOB_CREATED", "Job", new_job.id, {"title": new_job.title}, is_critical=True)
        db.commit() # Explicit commit for audit log in this test
        print("Audit log created successfully")

    except Exception as e:
        db.rollback()
        print(f"Error in creation: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_create_job()
