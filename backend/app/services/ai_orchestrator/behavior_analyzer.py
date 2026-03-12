import json
import logging
from typing import List, Dict
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def analyze_behavior(transcript: List[Dict[str, str]]) -> dict:
    """Analyzes the entire interview transcript for behavioral insights."""
    logger.info("Analyzing full interview transcript for behavioral insights")
    
    # Pre-process transcript to string
    chat_log = ""
    for entry in transcript:
        role = entry.get('role', 'unknown')
        text = entry.get('text', '')
        chat_log += f"{role.upper()}: {text}\n"
        
    system_prompt = f"""
    You are an expert HR organizational psychologist. Analyze the following interview transcript and extract behavioral insights.
    
    Focus on:
    - Problem-solving approach
    - Communication clarity
    - Response to pressure/difficult questions
    - Coachability
    
    Transcript:
    {chat_log}
    
    Return a JSON object with:
    - 'strengths' (list of strings)
    - 'weaknesses' (list of strings)
    - 'behavioral_score' (float 0-10)
    - 'summary' (string)
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0.3
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to analyze behavior: {str(e)}", exc_info=True)
        return {
            "strengths": ["Completed interview"],
            "weaknesses": ["Unable to generate full behavioral profile"],
            "behavioral_score": 5.0,
            "summary": "Behavioral analysis failed or incomplete."
        }
