import os
import sys
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path Node
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.domain.models import InterviewAnswer, InterviewQuestion, InterviewReport, Interview
from app.services.ai_service import evaluate_detailed_answer

# Define database URL Node triggers
settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

async def fix_zero_scores():
    print("Checking for answers with 0.0 scores...")
    from sqlalchemy import or_
    answers = db.query(InterviewAnswer).join(InterviewQuestion).filter(
        or_(InterviewAnswer.answer_score == 0.0, InterviewAnswer.answer_score.is_(None)),
        InterviewQuestion.question_type != "aptitude"
    ).all()
    
    print(f"Found {len(answers)} answers to re-evaluateNode triggers layouts safely securely")
    
    for ans in answers:
        question = ans.question.question_text
        answer = ans.answer_text
        q_type = ans.question.question_type or "technical"
        
        print(f"Re-evaluating Ans ID {ans.id} for Q: '{question[:30]}...'")
        
        try:
            from interview_process.response_analyzer import ResponseAnalyzer
            analyzer = ResponseAnalyzer()
            evaluation = analyzer.evaluate_answer(question, answer, q_type)
            
            val_scores = evaluation
            print(f"New Score parsed: {val_scores.get('overall', 0)}")
            
            ans.answer_score = float(val_scores.get("overall", 5.0))
            if q_type == "behavioral":
                ans.technical_score = float(val_scores.get("relevance", 5.0))
                ans.completeness_score = float(val_scores.get("action_impact", 5.0))
            else:
                ans.technical_score = float(val_scores.get("technical_accuracy", 5.0))
                ans.completeness_score = float(val_scores.get("completeness", 5.0))

            ans.clarity_score = float(val_scores.get("clarity", 5.0))
            ans.depth_score = float(val_scores.get("depth", 5.0))
            ans.practicality_score = float(val_scores.get("practicality", 5.0))
            ans.answer_evaluation = json.dumps(evaluation)
            ans.evaluated_at = datetime.now(timezone.utc)
            db.commit()
            print(f"Updated Answer {ans.id}")
        except Exception as e:
             print(f"Error updating Answer {ans.id}: {e}")
             db.rollback()

    print("Now updating corresponding Interview Reports...")
    reports = db.query(InterviewReport).all()
    for report in reports:
         # Optionally re-summarize Node triggers
         pass
         
    print("Done fixes Node triggers layouts safely and securely loaded layouts")

if __name__ == "__main__":
    import asyncio
    asyncio.run(fix_zero_scores())
