import sys
import uuid
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database import SessionLocal
from app.domain.models import User, Job, Application

def seed_data():
    db = SessionLocal()
    try:
        hr_user = db.query(User).filter(User.email == 'vigneshgovardhan5163@gmail.com').first()
        if not hr_user:
            print("HR User vigneshgovardhan5163@gmail.com not found.")
            # Let's fallback to the first 'hr' user we find
            hr_user = db.query(User).filter(User.role == 'hr').first()
            if not hr_user:
                 print("No HR user found at all! Start the frontend and register an HR account first.")
                 return

        print(f"Using HR user: {hr_user.email}")

        # Adding 2 Jobs
        job1 = Job(
            job_id=str(uuid.uuid4())[:8],
            interview_token=str(uuid.uuid4()),
            title="Senior Frontend Engineer (Test)",
            description="We are looking for an experienced React developer to build stunning user interfaces with modern frontend tooling.",
            experience_level="Senior",
            location="Remote",
            hr_id=hr_user.id,
            aptitude_enabled=False,
            first_level_enabled=True,
            interview_mode="ai",
            status="open",
            primary_evaluated_skills='["React", "TypeScript", "Tailwind CSS", "Next.js"]'
        )

        job2 = Job(
            job_id=str(uuid.uuid4())[:8],
            interview_token=str(uuid.uuid4()),
            title="Backend Data Engineer (Test)",
            description="Join our team to build scalable FastAPI services and robust data pipelines with Python and PostgreSQL.",
            experience_level="Mid-Level",
            location="New York",
            hr_id=hr_user.id,
            aptitude_enabled=True,
            first_level_enabled=True,
            interview_mode="ai",
            status="open",
            primary_evaluated_skills='["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker"]'
        )

        db.add_all([job1, job2])
        db.commit()

        # Adding 2 Applications
        app1 = Application(
            job_id=job1.id,
            candidate_name="Alice Developer",
            candidate_email="alice.test@example.com",
            resume_file_path="dummy_resume_alice.pdf",
            resume_file_name="alice_resume.pdf",
            status="submitted",
            hr_notes="Seems promising from the initial look."
        )

        app2 = Application(
            job_id=job2.id,
            candidate_name="Bob Backend",
            candidate_email="bob.test@example.com",
            resume_file_path="dummy_resume_bob.pdf",
            resume_file_name="bob_cv.pdf",
            status="submitted",
            hr_notes="Needs technical evaluation."
        )

        db.add_all([app1, app2])
        db.commit()

        print(f"Successfully seeded 2 jobs and 2 applications tied to HR: {hr_user.email}")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
