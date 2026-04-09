import sys
import os
sys.path.append(os.getcwd())

from app.infrastructure.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE interview_answers ADD COLUMN IF NOT EXISTS reasoning JSONB"))
        conn.commit()
        print("Successfully added reasoning to interview_answers")
    except Exception as e:
        print(f"Error adding to interview_answers: {e}")
        conn.rollback()

    try:
        conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN IF NOT EXISTS reasoning JSONB"))
        conn.commit()
        print("Successfully added reasoning to resume_extractions")
    except Exception as e:
        print(f"Error adding to resume_extractions: {e}")
        conn.rollback()
        
    try:
        conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN IF NOT EXISTS candidate_name VARCHAR(255)"))
        conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
        conn.execute(text("ALTER TABLE resume_extractions ADD COLUMN IF NOT EXISTS phone_number VARCHAR(50)"))
        conn.commit()
        print("Successfully added resume_extractions missing columns")
    except Exception as e:
        print(f"Error adding more columns to resume_extractions: {e}")
        conn.rollback()
