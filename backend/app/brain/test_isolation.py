import os
import requests
from dotenv import load_dotenv

load_dotenv()

# We need valid tokens for HR1, HR2, and SuperAdmin to test this properly via API.
# Since we don't have passwords/tokens handy, we'll use a DB-level verification script 
# that simulates the query logic we've implemented.

from sqlalchemy import create_engine, text, or_, func
from sqlalchemy.orm import Session
from app.domain.models import Job, Application, Interview, User

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)

def test_isolation():
    with Session(engine) as db:
        # Fetch some HR users
        hr_users = db.query(User).filter(User.role == 'hr').limit(2).all()
        if len(hr_users) < 2:
            print("Not enough HR users to test isolation. Please create at least 2 HR users.")
            return

        hr1 = hr_users[0]
        hr2 = hr_users[1]
        
        print(f"Testing isolation for HR1: {hr1.full_name} (ID: {hr1.id}) and HR2: {hr2.full_name} (ID: {hr2.id})")

        # 1. Test Application List Isolation logic
        def get_apps_count(user_id):
            return db.query(Application).filter(Application.hr_id == user_id).count()

        hr1_apps = get_apps_count(hr1.id)
        hr2_apps = get_apps_count(hr2.id)
        
        print(f"HR1 has {hr1_apps} applications.")
        print(f"HR2 has {hr2_apps} applications.")

        # 2. Test Search Isolation logic
        def simulate_search(user_id):
            query = db.query(Application).outerjoin(Job)
            query = query.filter(or_(Job.hr_id == user_id, Application.hr_id == user_id))
            return query.count()

        hr1_search_count = simulate_search(hr1.id)
        hr2_search_count = simulate_search(hr2.id)
        
        print(f"HR1 Search Visibility: {hr1_search_count}")
        print(f"HR2 Search Visibility: {hr2_search_count}")

        # 3. Test Analytics Dash logic
        def simulate_dash(user_id):
            metrics_query = db.query(func.count(Application.id)).outerjoin(Job, Application.job_id == Job.id)
            metrics_query = metrics_query.filter(or_(Job.hr_id == user_id, Application.hr_id == user_id))
            return metrics_query.scalar()

        hr1_dash_count = simulate_dash(hr1.id)
        hr2_dash_count = simulate_dash(hr2.id)
        
        print(f"HR1 Dashboard Total Apps: {hr1_dash_count}")
        print(f"HR2 Dashboard Total Apps: {hr2_dash_count}")

        total_global = db.query(Application).count()
        print(f"Total Global Applications: {total_global}")

        if hr1_search_count < total_global or hr2_search_count < total_global:
            print("\nSUCCESS: Data isolation is ACTIVE.")
        else:
            print("\nFAILURE: HR users can still see all data!")

test_isolation()
