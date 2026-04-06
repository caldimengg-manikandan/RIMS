import json
import logging
from typing import List, Dict
from app.services.ai_client import ai_client, clean_json

logger = logging.getLogger(__name__)

async def analyze_behavior(transcript: List[Dict[str, str]]) -> dict:
    """Analyzes the entire interview transcript for behavioral insights."""
    logger.info("Analyzing full interview transcript for behavioral insights")
    
    # Pre-process transcript to string
    chat_log = ""
    for entry in transcript:
        role = entry.get('role', 'unknown')
        text = entry.get('text', '')
        chat_log += f"{role.upper()}: {text}\n"
        
    prompt = f"Analyze the following interview transcript and extract behavioral insights.\n\nTranscript:\n{chat_log}"
    
    system_instr = """
    You are an expert HR organizational psychologist. 
    Analyze the transcript focusing on:
    - Problem-solving approach
    - Communication clarity
    - Response to pressure/difficult questions
    - Coachability
    
    Return a JSON object with:
    - 'strengths' (list of strings)
    - 'weaknesses' (list of strings)
    - 'behavioral_score' (float 0-10)
    - 'summary' (string)
    Return ONLY valid JSON.
    """
    
    try:
        response = await ai_client.generate(prompt, system_instr)
        return json.loads(clean_json(response))
    except Exception as e:
        logger.error(f"Failed to analyze behavior: {str(e)}", exc_info=True)
        return {
            "strengths": ["Completed interview"],
            "weaknesses": ["Unable to generate full behavioral profile"],
            "behavioral_score": 5.0,
            "summary": "Behavioral analysis failed or incomplete."
        }
