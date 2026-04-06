import sys
import os
sys.path.insert(0, os.getcwd())

from app.infrastructure.database import SessionLocal
from app.domain.models import Application, Job, User
from sqlalchemy import text

def test_db_write():
    db = SessionLocal()
    try:
        print("🔍 Testing Real DB Write Path (Supabase)...")
        # Ensure we have at least one job to link to
        job = db.query(Job).first()
        if not job:
            print("⚠️ No job found to link test application. Aborting write test.")
            return

        test_app = Application(
            job_id=job.id,
            candidate_name="System Reality Check",
            candidate_email="integrity@check.com",
            candidate_phone="GAAAAA_ENCRYPTED_PLACEHOLDER", # Using our encryption decorator
            status="applied"
        )
        db.add(test_app)
        db.commit()
        db.refresh(test_app)
        
        print(f"✅ Success! Record inserted with ID: {test_app.id}")
        
        # Cleanup
        db.delete(test_app)
        db.commit()
        print("🧹 Cleanup: Test record removed.")
    except Exception as e:
        print(f"❌ DB Write Failed: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_db_write()
