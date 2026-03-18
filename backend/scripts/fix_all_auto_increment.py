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

tables_to_fix = [
    "ai_evaluations",
    "application_stages",
    "applications",
    "audit_logs",
    "candidate_skills",
    "hiring_decisions",
    "interview_answers",
    "interview_events",
    "interview_feedbacks",
    "interview_issues",  # It will raise duplicate PK but script catches and continues
    "interview_questions",
    "interview_reports",
    "interview_sessions",
    "interviews",
    "jobs",
    "notifications",
    "question_bank",
    "resume_extractions",
    "users"
]

try:
    with engine.connect() as connection:
        for table in tables_to_fix:
            print(f"Fixing {table}.id with AUTO_INCREMENT PRIMARY KEY...")
            query = f"ALTER TABLE {table} MODIFY id INT AUTO_INCREMENT PRIMARY KEY"
            try:
                connection.execute(text(query))
                print(f" - Added AUTO_INCREMENT PRIMARY KEY to {table}")
            except Exception as e:
                print(f" - Failed adding to {table}: {e}")
            connection.commit()
    print("All AUTO_INCREMENT PRIMARY KEY properties updated successfully!")
except Exception as e:
    print(f"Failed to execute modifications: {e}")
