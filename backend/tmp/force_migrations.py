import sys
import os
sys.path.append(os.getcwd())

from app.infrastructure.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLS = [
    ("jobs", "aptitude_questions_file", "VARCHAR(500)"),
    ("applications", "resume_file_path", "VARCHAR(500)"),
    ("jobs", "job_id", "VARCHAR(50)"),
    ("interview_questions", "question_options", "TEXT"),
    ("interview_questions", "correct_option", "INTEGER"),
    ("resume_extractions", "summary", "TEXT"),
    ("jobs", "interview_token", "VARCHAR(50)"),
    ("interviews", "test_id", "VARCHAR(50)"),
    ("applications", "resume_status", "VARCHAR(32) DEFAULT 'pending'"),
    ("applications", "resume_score", "FLOAT DEFAULT 0"),
    ("applications", "aptitude_score", "FLOAT DEFAULT 0"),
    ("applications", "interview_score", "FLOAT DEFAULT 0"),
    ("applications", "composite_score", "FLOAT DEFAULT 0"),
    ("applications", "recommendation", "VARCHAR(50)"),
    ("resume_extractions", "candidate_name", "VARCHAR(255)"),
    ("resume_extractions", "email", "VARCHAR(255)"),
    ("resume_extractions", "phone_number", "VARCHAR(50)"),
    ("resume_extractions", "reasoning", "TEXT"),
    ("interviews", "current_difficulty", "VARCHAR(20) DEFAULT 'medium'"),
    ("interviews", "questions_asked", "INTEGER DEFAULT 0"),
    ("interviews", "total_questions", "INTEGER DEFAULT 20"),
    ("applications", "hr_id", "INTEGER"),
]

def force():
    # Set a very long timeout for this session
    with engine.connect() as conn:
        try:
            conn.execute(text("SET statement_timeout = '60s'"))
            conn.commit()
        except:
            pass
            
        for table, col, col_type in COLS:
            logger.info(f"Ensuring {table}.{col}...")
            try:
                # We do it one by one to avoid transaction abortion
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"))
                conn.commit()
                logger.info(f"DONE: {table}.{col}")
            except Exception as e:
                logger.warning(f"Failed {table}.{col}: {e}")
                # Reset connection if aborted
                # conn.rollback() # SQLAlchemy usually handle this or we can just continue if it didn't block
                
if __name__ == "__main__":
    force()
