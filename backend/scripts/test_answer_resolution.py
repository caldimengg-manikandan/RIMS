import os
import json
from datetime import datetime, timezone
from app.infrastructure.database import SessionLocal
from app.domain.models import Interview, InterviewQuestion, InterviewAnswer

def test_resolution():
    db = SessionLocal()
    try:
        interview_id = 120
        question_id = 1521
        
        # Mock data (what the frontend sends)
        submitted_index = "0"
        
        # Get question to verify options
        q = db.query(InterviewQuestion).filter(InterviewQuestion.id == question_id).first()
        if not q:
            print("Question not found")
            return
            
        print(f"Testing Question: {q.question_text}")
        print(f"Options: {q.options}")
        print(f"Submitted Index: {submitted_index}")

        # --- REPLICATING THE LOGIC FROM interviews.py ---
        stored_answer_text = submitted_index
        
        if q.question_type == "aptitude" and q.options:
            try:
                options = json.loads(q.options)
                if isinstance(options, list):
                    submitted_val = submitted_index.strip()
                    if submitted_val.isdigit():
                        idx = int(submitted_val)
                        if 0 <= idx < len(options):
                            stored_answer_text = str(options[idx])
                            print(f"SUCCESS: Resolved index {idx} to text: {stored_answer_text}")
            except Exception as e:
                print(f"ERROR: Failed to resolve index: {e}")
        # ------------------------------------------------

        if stored_answer_text == "64":
            print("VERIFICATION PASSED: Index 0 resolved to '64'")
        else:
            print(f"VERIFICATION FAILED: Expected '64', got '{stored_answer_text}'")

    finally:
        db.close()

if __name__ == "__main__":
    test_resolution()
