from app.infrastructure.database import SessionLocal
from app.domain.models import Job, Application, User
from app.domain.constants import CandidateState
import uuid
from datetime import datetime, timezone

def setup_audit_data():
    db = SessionLocal()
    try:
        # 1. Create Audit Job
        job = Job(
            title="AUDIT - Senior Software Architect",
            description="Special job created for deep functional testing. Required skills: Python, React, Kubernetes.",
            hr_id=34,
            experience_level="Senior",
            domain="Engineering",
            aptitude_enabled=True,
            first_level_enabled=True,
            status="open",
            primary_evaluated_skills="Python, React, API Design"
        )
        db.add(job)
        db.flush() # Get ID
        
        # 2. Create Audit Candidate
        candidate_email = f"audit_candidate_{uuid.uuid4().hex[:6]}@example.com"
        app = Application(
            job_id=job.id,
            candidate_name="Audit Candidate Alpha",
            candidate_email=candidate_email,
            status=CandidateState.APPLIED.value,
            resume_status="pending",
            applied_at=datetime.now(timezone.utc),
            hr_id=34
        )
        db.add(app)
        db.commit()
        print(f"SUCCESS: Created Audit Job ID {job.id} and Candidate ID {app.id}")
        return job.id, app.id
    except Exception as e:
        db.rollback()
        print(f"FAILURE: {e}")
        return None, None
    finally:
        db.close()

if __name__ == "__main__":
    setup_audit_data()
