
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "backend")))

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
# Mock settings if needed, but usually it reads from .env

from app.services.ai_service import parse_resume_with_ai

async def test_parse():
    resume_text = """
    John Doe
    Software Engineer
    Skills: Python, React, SQL, AWS.
    Experience: 5 years at TechCorp.
    Education: BS in Computer Science.
    """
    job_desc = "Seeking a Senior Python Developer with React experience."
    
    print("Testing AI Resume Parsing...")
    try:
        result = await parse_resume_with_ai(resume_text, 1, job_desc)
        print("Result:", result)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_parse())
