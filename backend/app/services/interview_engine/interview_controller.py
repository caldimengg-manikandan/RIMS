import logging

from app.core.config import get_settings
from app.core.ephemeral_result_cache import cache_get, cache_set
from app.core.idempotency import is_duplicate_request
from app.core.observability import log_json
from app.services.ai_orchestrator import evaluate_answer, generate_questions

from .adaptive_engine import adjust_difficulty
from .session_manager import session_manager

logger = logging.getLogger(__name__)
settings = get_settings()

from app.infrastructure.database import SessionLocal
from app.domain.models import Interview, InterviewQuestion, InterviewAnswer
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
settings = get_settings()

async def process_interview_message(session_id: str, data: dict):
    """Core logic controller backed by SQLAlchemy state."""
    db = SessionLocal()
    try:
        # 1. Fetch persistent session state
        interview_id = int(session_id) if str(session_id).isdigit() else 0
        interview = db.query(Interview).filter(Interview.id == interview_id).with_for_update().first()
        
        if not interview:
            await session_manager.send_personal_message({"type": "error", "message": "Invalid session."}, session_id)
            return

        action = data.get("action")
        
        # 2. Resuming logic in ACTION=START
        if action == "start":
            if interview.status == "not_started":
                interview.status = "in_progress"
                interview.started_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Starting fresh adaptive interview for ID {interview_id}")
            else:
                logger.info(f"Resuming existing interview for ID {interview_id} (Question {interview.questions_asked})")

            # If we've already asked questions, fetch the most recent unanswered one
            current_q = db.query(InterviewQuestion).filter(
                InterviewQuestion.interview_id == interview_id
            ).order_by(InterviewQuestion.question_number.desc()).first()
            
            if current_q:
                # Check if it was answered
                ans = db.query(InterviewAnswer).filter(InterviewAnswer.question_id == current_q.id).first()
                if not ans:
                    # Send existing question
                    await session_manager.send_personal_message({
                        "type": "question",
                        "question": current_q.question_text,
                        "difficulty": interview.current_difficulty or "medium",
                        "resumed": True
                    }, session_id)
                    return

            await _generate_and_send_next_question(db, interview, session_id)
            
        elif action == "submit_answer":
            answer_text = data.get("answer", "")
            # Find current active question
            current_q = db.query(InterviewQuestion).filter(
                InterviewQuestion.interview_id == interview_id
            ).order_by(InterviewQuestion.question_number.desc()).first()

            if not current_q:
                await session_manager.send_personal_message({"type": "error", "message": "No active question."}, session_id)
                return

            # Idempotency / Already Answered check
            existing_ans = db.query(InterviewAnswer).filter(InterviewAnswer.question_id == current_q.id).first()
            if existing_ans:
                await session_manager.send_personal_message({"type": "system", "message": "Answer already received."}, session_id)
                return

            request_id = (data.get("request_id") or data.get("x_request_id") or "").strip()
            replay_key = f"idem:ws.interview.evaluation:{session_id}:{request_id}" if request_id else ""

            if request_id and settings.enable_request_id_idempotency:
                cached_eval = cache_get(replay_key)
                if cached_eval:
                    await session_manager.send_personal_message(cached_eval, session_id)
                    return

            # Immediate acknowledgment
            await session_manager.send_personal_message({"type": "system", "message": "Evaluating your answer..."}, session_id)

            # Evaluate answer using the rubric from the question (if available)
            rubric = current_q.expected_points if isinstance(current_q.expected_points, list) else []
            eval_result = await evaluate_answer(
                current_q.question_text,
                answer_text,
                rubric or ["Technical concept", "Practical application"]
            )

            # Persist the answer with detailed metrics
            ans = InterviewAnswer(
                interview_id=interview_id,
                question_id=current_q.id,
                answer_text=answer_text,
                answer_score=eval_result.get("technical_accuracy", 5.0),
                technical_score=eval_result.get("technical_accuracy", 5.0),
                completeness_score=eval_result.get("completeness", 5.0),
                clarity_score=eval_result.get("clarity", 5.0),
                depth_score=eval_result.get("depth", 5.0),
                practicality_score=eval_result.get("practicality", 5.0),
                answer_evaluation=json.dumps(eval_result)
            )
            db.add(ans)

            # Update difficulty and ask count
            new_difficulty = adjust_difficulty(interview.current_difficulty or "medium", eval_result.get("technical_accuracy", 5.0))
            interview.current_difficulty = new_difficulty
            interview.questions_asked += 1
            db.commit()

            eval_msg = {
                "type": "evaluation",
                "score": eval_result.get("technical_accuracy"),
                "feedback": eval_result.get("feedback_text"),
            }
            if request_id: cache_set(replay_key, eval_msg)
            await session_manager.send_personal_message(eval_msg, session_id)
            
            # Ending condition: 10 questions for full adaptive session
            if interview.questions_asked >= (interview.total_questions or 10):
                interview.status = "completed"
                interview.ended_at = datetime.now(timezone.utc)
                db.commit()
                
                # Critical: Trigger final report generation for WebSocket interviews
                try:
                    from app.api.interviews import _finalize_interview_and_report_internal
                    await _finalize_interview_and_report_internal(db, interview_id)
                except Exception as final_err:
                    logger.error(f"Failed to auto-generate report on finish: {final_err}")
                
                await session_manager.send_personal_message({"type": "end", "message": "Interview Complete. Grading..."}, session_id)
            else:
                await _generate_and_send_next_question(db, interview, session_id)

    except Exception as e:
        logger.error(f"WS Controller Error: {e}", exc_info=True)
        db.rollback()
        await session_manager.send_personal_message({"type": "error", "message": "Internal processing error."}, session_id)
    finally:
        db.close()

async def _generate_and_send_next_question(db, interview, session_id: str):
    """Generate next question based on current difficulty and history."""
    # Fetch history for context
    history_ans = db.query(InterviewAnswer).filter(InterviewAnswer.interview_id == interview.id).all()
    history_context = [{"question": "Previously asked", "answer": a.answer_text} for a in history_ans] # Minimal summary

    # Simplified skill context for generator
    skills = ["Software Engineering"]
    if interview.application and interview.application.job:
        skills = [interview.application.job.title]

    question_data_list = await generate_questions(
        skills[0], 
        "Any", 
        skills, 
        history_context, 
        interview.current_difficulty or "medium"
    )
    
    # Extract question and rubric
    question_text = "Describe your experience with production systems."
    expected_points = ["Technical depth", "Problem solving"]
    
    if isinstance(question_data_list, dict):
        question_text = question_data_list.get("question", question_text)
        expected_points = question_data_list.get("expected_points", expected_points)
    elif isinstance(question_data_list, list) and len(question_data_list) > 0:
        # Fallback for older list-based legacy response
        question_text = question_data_list[0]

    # Persist the question with its rubric
    new_q = InterviewQuestion(
        interview_id=interview.id,
        question_number=interview.questions_asked + 1,
        question_text=question_text,
        question_type="adaptive",
        expected_points=expected_points
    )
    db.add(new_q)
    db.commit()

    await session_manager.send_personal_message({
        "type": "question",
        "question": question_text,
        "difficulty": interview.current_difficulty or "medium"
    }, session_id)
