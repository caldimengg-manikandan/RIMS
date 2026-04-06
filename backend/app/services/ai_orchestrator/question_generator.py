import json
import logging
from typing import List, Dict
from app.services.ai_client import ai_client, clean_json, is_ai_unavailable_response

logger = logging.getLogger(__name__)

async def generate_questions(role: str, experience_level: str, skills: List[str], previous_evaluations: List[Dict] = None, difficulty: str = "medium") -> dict:
    """Generates the next interview question based on role, skills, and current difficulty."""
    logger.info(f"Generating {difficulty} question for {role}")
    
    # build prompt context based on how they did earlier
    context_str = "No prior questions yet."
    if previous_evaluations:
        context_str = json.dumps(previous_evaluations[-3:]) # Only check last 3 to keep context window clean
        
    prompt = f"""
    The candidate is applying for: {experience_level} {role}.
    The candidate has the following skills: {', '.join(skills)}.
    The current difficulty level requested is: {difficulty.upper()}.
    
    Context from recent questions:
    {context_str}
    
    Generate the next question.
    """
    
    system_instr = """
    You are an expert technical interviewer.
    Return a JSON object containing:
    - 'question': The exact question to ask the candidate.
    - 'expected_points': A list of strings of what a good answer should contain.
    - 'difficulty': The difficulty of the question.
    
    If the candidate is struggling based on recent context, ensure the question helps them regain confidence but tests fundamental concepts.
    Return ONLY valid JSON.
    """
    
    try:
        response = await ai_client.generate(prompt, system_instr)
        if is_ai_unavailable_response(response):
            raise ValueError("ai_unavailable")
        return json.loads(clean_json(response))
    except Exception as e:
        logger.error(f"Failed to generate question: {str(e)}", exc_info=True)
        return {"question": "Can you walk me through your most recent project and the technical challenges you faced?", "expected_points": ["Clear explanation", "Technical depth", "Problem solving"]}
