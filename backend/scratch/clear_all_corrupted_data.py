import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database import SessionLocal
from app.domain.models import (
    Application, Notification, ResumeExtraction, 
    InterviewAnswer, InterviewReport, HiringDecision,
    ApplicationStage, AuditLog
)
from app.core.encryption import decrypt_field

def clear_all_corrupted_data():
    db = SessionLocal()
    try:
        tables_to_check = [
            (Notification, "message"),
            (Application, "candidate_phone"),
            (Application, "hr_notes"),
            (Application, "candidate_phone_raw"),
            (ApplicationStage, "evaluation_notes"),
            (ResumeExtraction, "extracted_text"),
            (InterviewAnswer, "answer_text"),
            (InterviewAnswer, "answer_evaluation"),
            (InterviewReport, "summary"),
            (InterviewReport, "strengths"),
            (InterviewReport, "weaknesses"),
            (InterviewReport, "detailed_feedback"),
            (HiringDecision, "decision_comments"),
            (AuditLog, "details")
        ]
        
        total_deleted = 0
        total_cleared_fields = 0
        
        for model, field_name in tables_to_check:
            print(f"Checking {model.__tablename__}.{field_name}...")
            records = db.query(model).all()
            for rec in records:
                val = getattr(rec, field_name)
                if val and decrypt_field(val) == "[DECRYPTION_ERROR]":
                    if model in [Notification, AuditLog]:
                        # For these, just delete the whole row
                        print(f"  Deleting corrupted {model.__tablename__} (ID: {rec.id})")
                        db.delete(rec)
                        total_deleted += 1
                    else:
                        # For others, clear the field so the record remains usable
                        print(f"  Clearing corrupted field {field_name} in {model.__tablename__} (ID: {rec.id})")
                        setattr(rec, field_name, None)
                        total_cleared_fields += 1
            db.commit() # Commit per table to avoid huge transactions
            
        print(f"\nCleanup Complete!")
        print(f"Total records deleted: {total_deleted}")
        print(f"Total fields cleared: {total_cleared_fields}")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_corrupted_data()
