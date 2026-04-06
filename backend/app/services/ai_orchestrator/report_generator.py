import json
import logging
from typing import Dict
from app.services.ai_client import ai_client, clean_json

logger = logging.getLogger(__name__)

async def generate_final_report(candidate_info: dict, scores: dict, behavioral_insights: dict) -> dict:
    """Consolidates all scores and insights into a final hiring recommendation."""
    logger.info("Generating final hiring recommendation report")
    
    prompt = f"""
    Candidate Info: {json.dumps(candidate_info)}
    Scores (Technical, Communication, Reasoning, etc.): {json.dumps(scores)}
    Behavioral Insights: {json.dumps(behavioral_insights)}
    
    Generate the final executive summary for the hiring manager.
    """
    
    system_instr = """
    You are the final decision-making AI for an enterprise hiring pipeline.
    Output a JSON object with:
    - 'recommendation': MUST BE ONE OF ["STRONG_HIRE", "HIRE", "HOLD", "NO_HIRE"]
    - 'executive_summary': A concise 3-4 sentence summary of why this decision was made.
    Return ONLY valid JSON.
    """
    
    try:
        response = await ai_client.generate(prompt, system_instr)
        return json.loads(clean_json(response))
    except Exception as e:
        logger.error(f"Failed to generate final report: {str(e)}", exc_info=True)
        return {
            "recommendation": "HOLD",
            "executive_summary": "System error prevented full report generation. Manual HR review required."
        }
