import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# App components
from app.domain.models import Job, User
from app.api.jobs import list_jobs

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
SessionLocal = sessionmaker(bind=engine)

def inspect_query_logic():
    print("--- Inspecting list_jobs Query Logic ---")
    db = SessionLocal()
    try:
        # Simulate Aashif (ID 28)
        user_a = db.query(User).filter(User.id == 28).first()
        print(f"User: {user_a.email}, ID: {user_a.id}, Role: {user_a.role}")
        
        # We'll use a mock Depends replacement for the call
        # but simpler: just run the logic manually from jobs.py
        query = db.query(Job)
        if user_a.role.lower() == "hr":
            query = query.filter(Job.hr_id == user_a.id)
            
        print("\nGenerated SQL:")
        print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        
        results = query.all()
        print(f"\nResults count: {len(results)}")
        for r in results:
            print(f"Job ID: {r.id}, HR_ID: {r.hr_id}, Title: {r.title}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_query_logic()
