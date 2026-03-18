import json
import logging
from typing import Dict
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=15.0)

async def generate_final_report(candidate_info: dict, scores: dict, behavioral_insights: dict) -> dict:
    """Consolidates all scores and insights into a final hiring recommendation."""
    logger.info("Generating final hiring recommendation report")
    
    system_prompt = f"""
    You are the final decision-making AI for an enterprise hiring pipeline.
    
    Candidate Info: {json.dumps(candidate_info)}
    Scores (Technical, Communication, Reasoning, etc.): {json.dumps(scores)}
    Behavioral Insights: {json.dumps(behavioral_insights)}
    
    Generate the final executive summary for the hiring manager.
    Output a JSON object with:
    - 'recommendation': MUST BE ONE OF ["STRONG_HIRE", "HIRE", "HOLD", "NO_HIRE"]
    - 'executive_summary': A concise 3-4 sentence summary of why this decision was made.
    """
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to generate final report: {str(e)}", exc_info=True)
        return {
            "recommendation": "HOLD",
            "executive_summary": "System error prevented full report generation. Manual HR review required."
        }
