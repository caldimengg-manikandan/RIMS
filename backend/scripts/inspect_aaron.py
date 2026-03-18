import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.domain.models import InterviewAnswer, Interview, Application

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def inspect_aaron():
    print("Searching for Candidate Aaron Node Node NodeNode Node triggers triggers Node")
    answers = db.query(InterviewAnswer).join(Interview, InterviewAnswer.interview_id == Interview.id).join(Application, Interview.application_id == Application.id).filter(
        Application.candidate_name.ilike("%aaron%")
    ).all()
    
    print(f"Aaron Answers found: {len(answers)}")
    for ans in answers:
         print(f"ID: {ans.id}, Q_ID: {ans.question_id}, Score: {ans.answer_score}, Evaluation: {ans.answer_evaluation[:40] if ans.answer_evaluation else None}")

if __name__ == "__main__":
    inspect_aaron()
