from app.infrastructure.database import SessionLocal
from app.domain.models import Application, HiringDecision
from app.domain.constants import CandidateState
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chaos-tester")

TEST_APP_ID = 315

def run_scenario_1():
    db = SessionLocal()
    app = db.query(Application).get(TEST_APP_ID)
    if not app:
        print(f"App {TEST_APP_ID} not found")
        return

    print(f"--- [CHAOS TEST] Scenario 1: DB Failure ---")
    
    # Pre-test Setup: Set to a state that allows HIRE
    print(f"Setting App {TEST_APP_ID} to 'interview_completed'...")
    old_status = app.status
    app.status = 'interview_completed'
    db.commit()
    
    print(f"Status set to: {app.status}")
    
    # We can't easily call the API here without auth headers, 
    # so we'll call the service/logic directly which has the chaos injection.
    
    from app.api.decisions import hire_candidate
    from fastapi import Request, UploadFile
    import io

    # Mocking arguments for hire_candidate
    # (Checking function signature in decisions.py)
    # def hire_candidate(application_id: int, joining_date: str, notes: str, offer_letter: UploadFile, current_user, db)
    
    class MockUser: id = 1
    class MockFile:
        content_type = "application/pdf"
        async def read(self): return b"PDF CONTENT"

    print("Executing hire_candidate (with chaos injection)...")
    try:
        import asyncio
        asyncio.run(hire_candidate(
            application_id=TEST_APP_ID,
            joining_date="2026-05-01",
            notes="Chaos Test Hire",
            offer_letter=MockFile(),
            current_user=MockUser(),
            db=db
        ))
        print("RESULT: FAILURE (Logic did not raise exception as expected)")
    except RuntimeError as e:
        print(f"RESULT: SUCCESS (Caught expected chaos injection: {e})")
    except Exception as e:
        print(f"RESULT: UNEXPECTED ERROR: {type(e).__name__}: {e}")

    # Post-test Verification
    db.expire_all()
    app = db.query(Application).get(TEST_APP_ID)
    print(f"Final Status: {app.status}")
    
    # Verify no HiringDecision was created
    decision = db.query(HiringDecision).filter(HiringDecision.application_id == TEST_APP_ID).first()
    print(f"HiringDecision record exists: {decision is not None}")

    if app.status == 'interview_completed' and not decision:
        print("VERDICT: RESILIENT (Rollback successful, state preserved)")
    else:
        print("VERDICT: FAILED (System reached corrupted state)")
    
    # Restore
    # app.status = old_status
    # db.commit()

if __name__ == "__main__":
    run_scenario_1()
