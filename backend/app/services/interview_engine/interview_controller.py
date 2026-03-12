import logging
from app.services.ai_orchestrator import generate_questions, evaluate_answer
from .session_manager import session_manager
from .adaptive_engine import adjust_difficulty

logger = logging.getLogger(__name__)

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
            
        logger.info(f"Evaluating answer for session {session_id}")
        
        # 1. Send immediate acknowledgment
        await session_manager.send_personal_message({"type": "system", "message": "Evaluating your answer..."}, session_id)
        
        # 2. Evaluate answer
        eval_result = await evaluate_answer(
            state["current_question"]["question"], 
            answer_text, 
            state["current_question"]["expected_points"]
        )
        
        # 3. Store in history
        state["history"].append({
            "question": state["current_question"],
            "answer": answer_text,
            "evaluation": eval_result
        })
        
        # 4. Give feedback to candidate (optional in real interviews, but good for demo)
        await session_manager.send_personal_message({
            "type": "evaluation",
            "score": eval_result.get("technical_score"),
            "feedback": eval_result.get("feedback_text")
        }, session_id)
        
        # 5. Adaptive difficulty engine
        new_difficulty = adjust_difficulty(state["difficulty"], eval_result.get("technical_score", 5.0))
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
