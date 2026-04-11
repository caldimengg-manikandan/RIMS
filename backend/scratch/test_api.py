from app.infrastructure.database import SessionLocal
from app.domain.models import Application, User
from app.api.applications import get_hr_applications
from app.domain.schemas import ApplicationListResponse
import logging

logging.basicConfig(level=logging.DEBUG)

def test_api():
    db = SessionLocal()
    try:
        hr_user = db.query(User).filter(User.role == "super_admin").first()
        if not hr_user:
            print("No super_admin found")
            return
            
        print("Calling get_hr_applications...")
        result = get_hr_applications(
            db=db,
            current_user=hr_user,
            skip=0,
            limit=49,
            job_id=None,
            status="all",
            search=None,
            from_date=None,
            to_date=None,
            time_range=None
        )
        
        print("Raw result keys:", result.keys())
        print("Number of items:", len(result["items"]))
        
        print("Validating through Pydantic Model...")
        validated = ApplicationListResponse(**result)
        print("Validation successful!")
        
    except Exception as e:
        print("----- ERROR ENCOUNTERED -----")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_api()
