from app.infrastructure.database import SessionLocal
from app.domain.models import Application, User
from app.services.state_machine import CandidateStateMachine, TransitionAction
import time

TEST_APP_ID = 315

def run_idempotency_test():
    db = SessionLocal()
    try:
        # 1. Setup candidate in consistent state
        app = db.query(Application).get(TEST_APP_ID)
        app.status = "interview_completed"
        db.commit()
        
        # 2. Get a valid user ID (HR or Admin)
        hr_user = db.query(User).filter(User.role == "super_admin").first()
        if not hr_user:
             print("ERROR: No super_admin found for test")
             return
             
        user_id = hr_user.id
        fsm = CandidateStateMachine(db)
        
        print(f"--- [RELIABILITY TEST] Idempotency Check (App {TEST_APP_ID}) ---")
        
        # 3. First transition
        print("Request 1: Transitioning to 'review_later'...")
        res1 = fsm.transition(app, TransitionAction.REVIEW_LATER, user_id=user_id)
        db.commit()
        print(f"  Result 1: {res1.from_state} -> {res1.to_state}")
        
        # 4. Immediate second identical transition
        print("\nRequest 2 (IDENTICAL): Retrying transition immediately...")
        res2 = fsm.transition(app, TransitionAction.REVIEW_LATER, user_id=user_id)
        db.commit()
        print(f"  Result 2: {res2.from_state} -> {res2.to_state}")
        
        if res1.to_state == res2.to_state and res2.from_state == res2.to_state:
            print("\nVERDICT: RESILIENT (Duplicate transition suppressed via Idempotency Guard)")
        else:
            print("\nVERDICT: VULNERABLE (Duplicate transition processed or failed incorrectly)")
            
    finally:
        db.close()

if __name__ == "__main__":
    run_idempotency_test()
