import json
import logging
from typing import List
from app.core.observability import log_json, filter_pii
from app.services.ai_client import ai_client, clean_json, is_ai_unavailable_response

logger = logging.getLogger(__name__)

async def evaluate_answer(question: str, answer: str, expected_points: List[str]) -> dict:
    """Evaluates a single answer and returns scored metrics."""
    logger.info(f"Evaluating answer for question: {question[:50]}...")
    
    prompt = f"""
    Question Asked: {question}
    Expected Key Points: {', '.join(expected_points)}
    Candidate's Answer: {answer}
    
    Evaluate the candidate's answer based on the expected points and overall technical depth.
    """
    
    system_instr = """
    You are an AI interviewer evaluating a candidate's answer.
    Return a JSON object with EXACTLY the following fields: 
    - 'technical_accuracy' (float 0-10)
    - 'completeness' (float 0-10)
    - 'clarity' (float 0-10)
    - 'depth' (float 0-10)
    - 'practicality' (float 0-10)
    - 'strengths' (list of strings, constructively outlining positives)
    - 'weaknesses' (list of strings, constructively outlining negatives/gaps)
    - 'feedback_text' (string summarizing constructive feedback)
    - 'reasoning' (string, brief 1-sentence justification for the internal scoring)
    Return ONLY valid JSON.
    """
    
    try:
        response = await ai_client.generate(prompt, system_instr)
        if is_ai_unavailable_response(response):
             raise ValueError("ai_unavailable")
             
        data = json.loads(clean_json(response))
        if "reasoning" in data:
            data["reasoning"] = filter_pii(str(data["reasoning"]))
        return data
        
    except Exception as e:
        logger.error(f"Failed to evaluate answer: {str(e)}", exc_info=True)
        return {
            "technical_accuracy": 5.0,
            "completeness": 5.0,
            "clarity": 5.0,
            "depth": 5.0,
            "practicality": 5.0,
            "strengths": [],
            "weaknesses": [],
            "feedback_text": "Failed to parse answer evaluation due to an error.",
            "reasoning": "Heuristic fallback evaluation due to AI parsing error."
        }
