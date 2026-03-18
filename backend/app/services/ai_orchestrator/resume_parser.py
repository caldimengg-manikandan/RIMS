import json
import logging
from openai import AsyncOpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def parse_resume(text: str) -> dict:
    """Extracts structured fields from raw resume text."""
    logger.info("Parsing resume with AI Orchestrator")
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert technical recruiter. Parse the resume and return a JSON object with: 'skills' (list of strings), 'years_of_experience' (float), 'education' (list of objects), 'previous_roles' (list of objects with 'title', 'company', 'duration'), 'summary' (string)."},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Failed to parse resume: {str(e)}", exc_info=True)
        # Fallback mechanism
        return {"skills": [], "years_of_experience": 0, "education": [], "previous_roles": [], "summary": "Failed to parse."}
