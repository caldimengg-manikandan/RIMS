import os
import sys
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, select
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

# We want to stress process_application_background
from app.api.applications import process_application_background
from app.domain.models import Application, ResumeExtraction, Job

async def simulate_background_processing(app_id, job_id, resume_path):
    # Each thread needs its own DB session to simulate concurrent workers
    db = SessionLocal()
    try:
        print(f" -> Thread starting trigger for App {app_id}")
        # Note: process_application_background is technically synchronous in definition 
        # but we can wrap it or call it in thread pools.
        await asyncio.to_thread(process_application_background, app_id, job_id, resume_path, "test@test.com", "Validation Candidate")
        print(f" -> Thread finished App {app_id}")
    except Exception as e:
         print(f" -> Thread Errored: {e}")
    finally:
         db.close()

async def chaos_test():
    print("--- STARTING CHAOS CONCURRENCY SIMULATION ---")
    
    db = SessionLocal()
    try:
        # Piquing an Application
        app = db.query(Application).first()
        if not app:
             print("No applications found to stress test. Run verify_connection_deep.py first.")
             return
             
        app_id = app.id
        job_id = app.job_id
        path = "uploads/resumes/dummy.pdf" # dummy path
        
        # Ensure we have a dummy file there
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
             f.write("Validation test resume data. Python Postgres Docker.")

        print(f"Targeting Application ID: {app_id} with parallel triggers")
        
        # Verify initial count
        init_count = db.query(ResumeExtraction).filter(ResumeExtraction.application_id == app_id).count()
        print(f"Initial ResumeExtraction count for App {app_id}: {init_count}")

        # Spawn 10 concurrent workers
        tasks = []
        for i in range(10):
             tasks.append(simulate_background_processing(app_id, job_id, path))
             
        print("\nFiring 10 concurrent streams...")
        await asyncio.gather(*tasks)
        print("\nAll concurrent streams finished.")

        # Final Verification
        db.expire_all()
        final_count = db.query(ResumeExtraction).filter(ResumeExtraction.application_id == app_id).count()
        print(f"Final ResumeExtraction count for App {app_id}: {final_count}")
        
        if final_count == 1:
             print("--- SUCCESS: Concurrency check locked out double-inserts correctly. ---")
        else:
             print(f"--- FAILURE: Found {final_count} entries. Lock failed. ---")

    except Exception as e:
         print(f"Chaos error: {e}")
    finally:
         db.close()

if __name__ == "__main__":
    asyncio.run(chaos_test())
