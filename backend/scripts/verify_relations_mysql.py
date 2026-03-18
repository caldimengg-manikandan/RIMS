import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print("DATABASE_URL not found")
    exit(1)

print(f"Connecting to: {db_url}")
engine = create_engine(db_url)

try:
    with engine.connect() as connection:
        # Check users
        users = connection.execute(text("SELECT id, email, role FROM users")).fetchall()
        print("\n--- Users ---")
        for u in users:
            print(f" - ID: {u[0]}, Email: {u[1]}, Role: {u[2]}")
            
        # Check jobs
        jobs = connection.execute(text("SELECT id, title, hr_id, status FROM jobs")).fetchall()
        print("\n--- Jobs ---")
        for j in jobs:
            print(f" - ID: {j[0]}, Title: {j[1]}, HR_ID: {j[2]}, Status: {j[3]}")
    
        applications = connection.execute(text("SELECT id, job_id, candidate_name, status FROM applications")).fetchall()
        print("\n--- Applications ---")
        for a in applications:
             print(f" - ID: {a[0]}, Job_ID: {a[1]}, Candidate: {a[2]}, Status: {a[3]}")

except Exception as e:
    print(f"Failed to inspect: {e}")
