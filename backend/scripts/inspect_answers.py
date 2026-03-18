import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.domain.models import InterviewAnswer, InterviewQuestion

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def inspect():
    answers = db.query(InterviewAnswer).all()
    print(f"Total Answers in DB: {len(answers)}")
    
    for ans in answers[:10]:
         print(f"ID: {ans.id}, Score: {ans.answer_score}, Question ID: {ans.question_id}")

if __name__ == "__main__":
    inspect()
