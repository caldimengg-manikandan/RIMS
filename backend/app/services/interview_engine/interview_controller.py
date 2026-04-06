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

# In-memory store for ongoing interviews (Mock Database for now)
interview_state = {}

async def process_interview_message(session_id: str, data: dict):
    """Core logic controller for a live interview session"""
    
    action = data.get("action")
    
    if session_id not in interview_state:
        interview_state[session_id] = {
            "role": "Software Engineer",
            "experience": "Mid-Level",
            "skills": ["Python", "FastAPI", "React"],
            "difficulty": "medium",
            "history": [],
            "current_question": None
        }
        
    state = interview_state[session_id]
    
    if action == "start":
        logger.info(f"Starting interview session {session_id}")
        await _generate_and_send_next_question(session_id, state)
        
    elif action == "submit_answer":
        answer_text = data.get("answer", "")
        if not state["current_question"]:
            await session_manager.send_personal_message({"type": "error", "message": "No active question."}, session_id)
            return

        request_id = (data.get("request_id") or data.get("x_request_id") or "").strip()
        replay_key = f"idem:ws.interview.evaluation:{session_id}:{request_id}" if request_id else ""

        # Idempotent retries: replay cached evaluation JSON; in-flight dupes get a soft wait message.
        if request_id and settings.enable_request_id_idempotency:
            cached_eval = cache_get(replay_key)
            if cached_eval is not None:
                log_json(
                    logger,
                    "ws_submit_answer_idempotent_replay",
                    level="info",
                    extra={"session_id": session_id, "request_id_prefix": request_id[:12]},
                )
                await session_manager.send_personal_message(cached_eval, session_id)
                return
            if is_duplicate_request(
                request_id=request_id,
                scope="ws.interview.submit_answer",
                key=session_id,
                ttl_seconds=90,
            ):
                await session_manager.send_personal_message(
                    {
                        "type": "system",
                        "message": "Still processing your previous answer…",
                    },
                    session_id,
                )
                return

        logger.info(f"Evaluating answer for session {session_id}")

        # 1. Send immediate acknowledgment
        await session_manager.send_personal_message({"type": "system", "message": "Evaluating your answer..."}, session_id)

        # 2. Evaluate answer
        eval_result = await evaluate_answer(
            state["current_question"]["question"],
            answer_text,
            state["current_question"]["expected_points"],
        )

        # 3. Store in history
        state["history"].append({
            "question": state["current_question"],
            "answer": answer_text,
            "evaluation": eval_result
        })

        # 4. Give feedback to candidate (optional in real interviews, but good for demo)
        eval_msg = {
            "type": "evaluation",
            "score": eval_result.get("technical_accuracy"),
            "feedback": eval_result.get("feedback_text"),
        }
        if request_id and settings.enable_request_id_idempotency:
            cache_set(replay_key, eval_msg, ttl_seconds=90)
        await session_manager.send_personal_message(eval_msg, session_id)
        
        # 5. Adaptive difficulty engine
        new_difficulty = adjust_difficulty(state["difficulty"], eval_result.get("technical_accuracy", 5.0))
        state["difficulty"] = new_difficulty
        
        # 6. Generate next question
        if len(state["history"]) >= 5: # Limit to 5 questions
            await session_manager.send_personal_message({"type": "system", "message": "Interview concluding. Generating report..."}, session_id)
            # In a real system, we'd trigger the report_generator.py here and close WS
            await session_manager.send_personal_message({"type": "end", "message": "Interview Complete."}, session_id)
        else:
            await _generate_and_send_next_question(session_id, state)

async def _generate_and_send_next_question(session_id: str, state: dict):
    question_data = await generate_questions(
        state["role"], 
        state["experience"], 
        state["skills"], 
        state["history"], 
        state["difficulty"]
    )
    state["current_question"] = question_data
    
    await session_manager.send_personal_message({
        "type": "question",
        "question": question_data["question"],
        "difficulty": state["difficulty"]
    }, session_id)
