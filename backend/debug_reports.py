from app.infrastructure.database import SessionLocal
from app.api.analytics import get_interview_reports
from app.domain.models import User
import json
import traceback

def test():
    db = SessionLocal()
    user = db.query(User).filter(User.id == 26).first()
    if not user:
        print("User 26 not found")
        return
    
    try:
        print("\n--- Testing Filter: Job ID 1 ---")
        data = get_interview_reports(db=db, current_user=user, job_id=1)
        print(f"Reports for Job 1: {len(data.get('reports', []))}")
        
        print("\n--- Testing Filter: Status 'Select' ---")
        data = get_interview_reports(db=db, current_user=user, status="Select")
        print(f"Reports with Status 'Select': {len(data.get('reports', []))}")
        
        print("\n--- Testing Filter: Status 'applied' ---")
        data = get_interview_reports(db=db, current_user=user, status="applied")
        print(f"Reports with Status 'applied': {len(data.get('reports', []))}")

        print("\n--- Testing Filter: Job ID 'All' & Status 'All' ---")
        data = get_interview_reports(db=db, current_user=user, job_id="All", status="All")
        print(f"Total Reports (All/All): {len(data.get('reports', []))}")

    except Exception as e:
        print(f"Error testing filters: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test()
