import threading
import time
import requests
import json
import uuid

# Configuration
BASE_URL = "http://localhost:10000"
APP_ID = 386 # The Audit Candidate Alpha created earlier
HR_ID = 34
ACTION = "approve_for_interview"

def trigger_transition(thread_id):
    print(f"[Thread {thread_id}] Sending transition request...")
    try:
        # We simulate the HR dashboard calling the transition endpoint
        # Note: We need a valid HR token or a way to bypass auth for this deep test
        # Since I'm running locally, I'll use a bypass header if available or just the raw service call
        
        # ACTUALLY, I'll use a python script that calls the StateMachine directly 
        # to test the logic isolation from HTTP overhead.
        pass

    except Exception as e:
        print(f"[Thread {thread_id}] Error: {e}")

# Revised strategy: Use a Python script that uses multiprocessing to call the StateMachine class directly.
# This avoids needing to manage JWTs for a local logic test.

STRESS_SCRIPT = """
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
"""

if __name__ == "__main__":
    with open("stress_executor.py", "w") as f:
        f.write(STRESS_SCRIPT)
    
    print("Stress executor created. Run it with: .\\venv\\Scripts\\python.exe stress_executor.py")
