
import multiprocessing
from app.infrastructure.database import SessionLocal
from app.services.state_machine import CandidateStateMachine
from app.domain.models import Application
from app.domain.constants import TransitionAction
import time

def worker(worker_id, app_id):
    db = SessionLocal()
    sm = CandidateStateMachine(db)
    app = db.query(Application).filter(Application.id == app_id).first()
    
    print(f"[Worker {worker_id}] Attempting transition for App {app_id}...")
    try:
        result = sm.transition(app, TransitionAction.APPROVE_FOR_INTERVIEW, user_id=34)
        print(f"[Worker {worker_id}] SUCCESS: Moved to {result.to_state}")
    except Exception as e:
        print(f"[Worker {worker_id}] FAILED: {str(e)[:100]}")
    finally:
        db.close()

if __name__ == '__main__':
    processes = []
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i, 386))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
