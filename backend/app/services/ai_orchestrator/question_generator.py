import json
import logging
from typing import List, Dict
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def generate_questions(role: str, experience_level: str, skills: List[str], previous_evaluations: List[Dict] = None, difficulty: str = "medium") -> dict:
    """Generates the next interview question based on role, skills, and current difficulty."""
    logger.info(f"Generating {difficulty} question for {role}")
    
    # build prompt context based on how they did earlier
    context_str = "No prior questions yet."
    if previous_evaluations:
        context_str = json.dumps(previous_evaluations[-3:]) # Only check last 3 to keep context window clean
        
    system_prompt = f"""
    You are an expert technical interviewer for a {experience_level} {role}.
    The candidate has the following skills: {', '.join(skills)}.
    The current difficulty level requested is: {difficulty.upper()}.
    
    Context from recent questions:
    {context_str}
    
    Return a JSON object containing the exact 'question' to ask the candidate, and 'expected_points' (a list of strings of what a good answer should contain). If the candidate is struggling based on recent context, ensure the question helps them regain confidence but tests fundamental concepts.
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate the next question."}
            ],
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to generate question: {str(e)}", exc_info=True)
        return {"question": "Can you walk me through your most recent project and the technical challenges you faced?", "expected_points": ["Clear explanation", "Technical depth", "Problem solving"]}
