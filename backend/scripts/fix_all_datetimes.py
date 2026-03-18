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

# Table to columns mapping that need to be DATETIME
datetime_fixes = {
    "ai_evaluations": ["created_at"],
    "application_stages": ["started_at", "completed_at", "created_at"],
    "applications": ["applied_at", "updated_at"],
    "audit_logs": ["created_at"],
    "hiring_decisions": ["decided_at", "created_at"],
    "interview_answers": ["submitted_at", "evaluated_at"],
    "interview_events": ["created_at"],
    "interview_feedbacks": ["created_at"],
    "interview_issues": ["created_at", "resolved_at"],
    "interview_questions": ["ai_generated_at", "created_at"],
    "interview_reports": ["created_at", "updated_at"],
    "interview_sessions": ["start_time", "end_time"],
    "interviews": ["started_at", "ended_at", "expires_at", "used_at", "aptitude_completed_at", "created_at", "updated_at"],
    "jobs": ["created_at", "updated_at", "closed_at"],
    "notifications": ["created_at", "read_at"],
    "question_bank": ["created_at"],
    "resume_extractions": ["created_at", "updated_at"],
    "users": ["otp_expiry", "created_at", "updated_at"]
}

try:
    with engine.connect() as connection:
        for table, columns in datetime_fixes.items():
            print(f"Fixing {table}...")
            for col in columns:
                query = f"ALTER TABLE {table} MODIFY COLUMN {col} DATETIME NULL"
                try:
                    connection.execute(text(query))
                    print(f" - Converted {col} to DATETIME")
                except Exception as e:
                    print(f" - Failed converting {col} inside {table}: {e}")
            connection.commit()
    print("All DateTimes updated successfully!")
except Exception as e:
    print(f"Failed to execute modifications: {e}")
