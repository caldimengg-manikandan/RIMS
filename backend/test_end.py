import asyncio
from app.infrastructure.database import SessionLocal
from app.api.interviews import end_interview
from app.domain.models import Interview

async def main():
    db = SessionLocal()
    try:
        # Get the first interview, or the one that is mostly complete
        interview = db.query(Interview).order_by(Interview.id.desc()).first()
        if not interview:
            print("No interview found")
            return
            
        print("Testing with interview id:", interview.id)
        res = await end_interview(interview_id=interview.id, interview_session=interview, db=db)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Error details:", e)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
