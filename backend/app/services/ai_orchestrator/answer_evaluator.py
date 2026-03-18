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
    Return a JSON object with EXACTLY the following fields: 
    - 'technical_accuracy' (float 0-10)
    - 'completeness' (float 0-10)
    - 'clarity' (float 0-10)
    - 'depth' (float 0-10)
    - 'practicality' (float 0-10)
    - 'strengths' (list of strings, constructively outlining positives)
    - 'weaknesses' (list of strings, constructively outlining negatives/gaps)
    - 'feedback_text' (string summarizing constructive feedback)
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
            "technical_accuracy": 5.0,
            "completeness": 5.0,
            "clarity": 5.0,
            "depth": 5.0,
            "practicality": 5.0,
            "strengths": [],
            "weaknesses": [],
            "feedback_text": "Failed to parse answer evaluation due to an error."
        }
