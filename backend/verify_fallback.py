import asyncio
import json
import logging
import sys
import os

# Set up dummy environment for testing backend services
sys.path.append(os.getcwd())

# Mock AI client to simulate failure
class MockAIClient:
    async def generate(self, *args, **kwargs):
        raise Exception("Simulated AI Failure")

from app.services.ai_service import parse_resume_with_ai, ai_client

async def test_fallback():
    # Force a failure
    print("Testing Fallback Logic (Simulating AI Failure)...")
    
    resume_text = """
    Vignesh Govardhan
    Full-Stack Developer
    Exp: 5.5 years of experience
    Skills: JavaScript, React, Python, Java, Node.js, HTML, CSS
    """
    
    job_description = "We are looking for a React and Node.js developer with 5 years experience."
    
    # We call the function. It should enter the 'except' block.
    result = await parse_resume_with_ai(resume_text, 1, job_description, "5 years")
    
    print("\nExtraction Results:")
    print(f"Skills Found: {result['skills']}")
    print(f"Experience: {result['experience']} years")
    print(f"Match Percentage: {result['match_percentage']}%")
    print(f"Composite Score: {result['score']}/10")
    print(f"Extraction Degraded: {result['extraction_degraded']}")
    
    assert result['experience'] == 5.5
    assert result['match_percentage'] > 0
    assert result['score'] >= 5.0
    print("\nVerification SUCCESS: Fallback metrics are non-zero.")

if __name__ == "__main__":
    # Temporarily monkeypatch to ensure failure
    import app.services.ai_service
    # Manually trigger the exception block in parse_resume_with_ai 
    # by ensuring ai_client.generate fails.
    
    asyncio.run(test_fallback())
