
import asyncio
import json
from app.services.ai_service import parse_resume_with_ai

async def main():
    resume_text = "Experienced software engineer with 10 years of Python and React experience. Education: BS in CS. Worked as Lead Developer."
    job_description = "Need a Python expert."
    
    print("Testing parse_resume_with_ai...")
    try:
        result = await parse_resume_with_ai(resume_text, 1, job_description)
        print("Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
