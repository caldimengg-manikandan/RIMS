import json
import logging
from typing import List
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def evaluate_answer(question: str, answer: str, expected_points: List[str]) -> dict:
    """Evaluates a single answer and returns scored metrics."""
    logger.info(f"Evaluating answer for question: {question[:50]}...")
    
    system_prompt = f"""
    You are an AI interviewer evaluating a candidate's answer.
    
    Question Asked: {question}
    Expected Key Points: {', '.join(expected_points)}
    Candidate's Answer: {answer}
    
    Evaluate the candidate's answer based on the expected points and overall technical depth.
    Return a JSON object with: 
    - 'technical_score' (float 0-10)
    - 'communication_score' (float 0-10)
    - 'reasoning_score' (float 0-10)
    - 'feedback_text' (string with constructive feedback)
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to evaluate answer: {str(e)}", exc_info=True)
        return {
            "technical_score": 5.0,
            "communication_score": 5.0,
            "reasoning_score": 5.0,
            "feedback_text": "Failed to parse answer evaluation due to an error."
        }
