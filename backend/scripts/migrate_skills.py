import asyncio
from sqlalchemy import text
from app.database import engine

def apply_migrations():
    with engine.begin() as conn:
        print("Checking/Adding primary_evaluated_skills to jobs table...")
        try:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN primary_evaluated_skills TEXT;"))
            print("Added primary_evaluated_skills successfully.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column primary_evaluated_skills already exists.")
            else:
                print(f"Error checking/adding primary_evaluated_skills: {e}")

        print("Checking/Adding evaluated_skills to interview_reports table...")
        try:
            conn.execute(text("ALTER TABLE interview_reports ADD COLUMN evaluated_skills TEXT;"))
            print("Added evaluated_skills successfully.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column evaluated_skills already exists.")
            else:
                print(f"Error checking/adding evaluated_skills: {e}")

if __name__ == "__main__":
    apply_migrations()
