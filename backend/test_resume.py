import asyncio
import os
import sys

# Add the backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.applications import process_application_background
from app.db.session import SessionLocal

async def main():
    print("Testing application 4 background process...")
    try:
        abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "resumes", "gapegi6565_indevgo_com_1_1773218508.366102.pdf")
        await process_application_background(
            application_id=4,
            job_id=1,
            abs_file_path=abs_path,
            candidate_email="gapegi6565@indevgo.com",
            candidate_name="John"
        )
        print("Success!")
    except Exception as e:
        print(f"Error test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
