import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# App components
from app.domain.models import Job, User, Application
from app.infrastructure.database import set_db_identity

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_cross_user_isolation():
    print("--- Cross-User Isolation Verification ---")
    
    # HR A (ID 28)
    # HR B (ID 29)
    hr_a_id = 28
    hr_b_id = 29
    
    # 1. Setup Phase
    db = SessionLocal()
    try:
        job_a = db.query(Job).filter(Job.hr_id == hr_a_id).first()
        job_b = db.query(Job).filter(Job.hr_id == hr_b_id).first()
        
        if not job_a:
            print("Creating job for HR A...")
            job_a = Job(title="HR A Private Job", hr_id=hr_a_id, status="open", job_id="VERIFY-A", description="Test job A", experience_level="mid")
            db.add(job_a)
            db.commit()
            db.refresh(job_a)
            
        if not job_b:
            print("Creating job for HR B...")
            job_b = Job(title="HR B Private Job", hr_id=hr_b_id, status="open", job_id="VERIFY-B", description="Test job B", experience_level="mid")
            db.add(job_b)
            db.commit()
            db.refresh(job_b)

        job_a_id = job_a.id
        job_b_id = job_b.id
        print(f"Job A (owned by {hr_a_id}): {job_a_id}")
        print(f"Job B (owned by {hr_b_id}): {job_b_id}")
    finally:
        db.close()

    # 2. Test SELECT as HR A (Using a single connection/transaction)
    print("\nTesting SELECT as HR A (ID 28)...")
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text("SET LOCAL app.current_user_id = :uid"), {"uid": str(hr_a_id)})
            
            # Check Jobs visibility as seen by DB
            res = conn.execute(text("SELECT id FROM jobs WHERE id = :jid"), {"jid": job_b_id})
            others_job = res.first()
            
            if others_job:
                print(f"!!! CRITICAL FAIL: HR A can see HR B's job {job_b_id} via RLS")
            else:
                print(f"SUCCESS: HR A cannot see HR B's job via RLS.")
            
            # Verify HR A can see their own
            res = conn.execute(text("SELECT id FROM jobs WHERE id = :jid"), {"jid": job_a_id})
            own_job = res.first()
            if own_job:
                print(f"SUCCESS: HR A can see their own job {job_a_id}")
            else:
                print(f"FAIL: HR A cannot even see their own job!")
            
            trans.rollback() # Clean up
        except Exception as e:
            print(f"Error during HR A test: {e}")
            if 'trans' in locals(): trans.rollback()

    # 3. Test SELECT as HR B
    print("\nTesting SELECT as HR B (ID 29)...")
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text("SET LOCAL app.current_user_id = :uid"), {"uid": str(hr_b_id)})
            
            res = conn.execute(text("SELECT id FROM jobs WHERE id = :jid"), {"jid": job_a_id})
            others_job = res.first()
            if others_job:
                print(f"!!! CRITICAL FAIL: HR B can see HR A's job {job_a_id} via RLS")
            else:
                print(f"SUCCESS: HR B cannot see HR A's job via RLS.")
            
            trans.rollback()
        except Exception as e:
            print(f"Error during HR B test: {e}")
            if 'trans' in locals(): trans.rollback()

if __name__ == "__main__":
    verify_cross_user_isolation()
