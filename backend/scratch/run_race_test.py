from app.infrastructure.database import SessionLocal
from app.domain.models import Application
from app.services.state_machine import CandidateStateMachine
from app.domain.constants import TransitionAction
import threading
import time

TEST_APP_ID = 315

def perform_transition(action_name, results):
    # Each thread needs its own DB session
    db = SessionLocal()
    try:
        app = db.query(Application).get(TEST_APP_ID)
        fsm = CandidateStateMachine(db)
        
        # Capture action enum
        action = getattr(TransitionAction, action_name)
        
        print(f"[Thread {action_name}] Starting transition...")
        # Simulate some delay to increase race window
        time.sleep(0.1) 
        
        res = fsm.transition(app, action, user_id=1)
        db.commit()
        results.append((action_name, "SUCCESS", res.to_state))
    except Exception as e:
        db.rollback()
        results.append((action_name, "ERROR", str(e)))
    finally:
        db.close()

def run_race_chaos():
    db = SessionLocal()
    app = db.query(Application).get(TEST_APP_ID)
    app.status = "interview_completed"
    db.commit()
    db.close()
    
    print(f"--- [CHAOS TEST] Scenario 4: Race Condition (App {TEST_APP_ID}) ---")
    print("Attempting simultaneous 'REVIEW_LATER' and 'HIRE'...")
    
    results = []
    t1 = threading.Thread(target=perform_transition, args=("REVIEW_LATER", results))
    t2 = threading.Thread(target=perform_transition, args=("HIRE", results))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    print("\nResults:")
    for r in results:
        print(f"  Action {r[0]}: {r[1]} -> {r[2]}")
    
    db = SessionLocal()
    final_app = db.query(Application).get(TEST_APP_ID)
    print(f"\nFinal DB Status: {final_app.status}")
    
    success_count = len([r for r in results if r[1] == "SUCCESS"])
    if success_count > 1:
        print("VERDICT: VULNERABLE (Multiple transitions succeeded on the same base state!)")
    else:
        print("VERDICT: RESILIENT (Race condition handled via DB isolation or locking)")
    
    db.close()

if __name__ == "__main__":
    run_race_chaos()
