import os
import re
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# App components
from app.domain.models import Job, User
from app.api.jobs import _validate_job_content

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def test_flexible_validation_logic():
    print("Testing flexible title validation logic...")
    
    # Test valid titles with new symbols
    valid_titles = [
        "Lead Dev: Python & AI Engineer!",
        "Senior Developer (Remote #1)",
        "Job with + and _ and *",
        "Frontend [React] Specialist",
        "Growth Manager = Marketing % Sales"
    ]
    
    for title in valid_titles:
        try:
            _validate_job_content(title, "Valid description with enough length and text.", db)
            print(f"PASS: '{title}' is now valid.")
        except Exception as e:
            print(f"FAIL: '{title}' rejected unexpectedly: {e}")

    # Test invalid title (no letters)
    invalid_title = "123 # @ !"
    try:
        _validate_job_content(invalid_title, "Valid description.", db)
        print(f"FAIL: '{invalid_title}' should have been rejected.")
    except Exception as e:
        print(f"PASS: '{invalid_title}' correctly rejected: {e}")

    # Test invalid title (too many repeated symbols)
    repeated_symbols = "Job.....!!!"
    try:
        _validate_job_content(repeated_symbols, "Valid description.", db)
        print(f"FAIL: '{repeated_symbols}' should have been rejected.")
    except Exception as e:
        print(f"PASS: '{repeated_symbols}' correctly rejected: {e}")

    db.close()

if __name__ == "__main__":
    test_flexible_validation_logic()
