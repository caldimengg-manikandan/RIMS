
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
import sys

DATABASE_URL = "mysql+pymysql://root:0000@localhost/rims_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    from app.domain.models import Application, ResumeExtraction
    
    apps = db.query(Application).order_by(Application.applied_at.desc()).limit(5).all()
    for app in apps:
        print(f"ID: {app.id}, Candidate: {app.candidate_name}, Email: {app.candidate_email}, Status: {app.status}")
        if app.resume_extraction:
            re = app.resume_extraction
            print(f"  Extraction ID: {re.id}")
            print(f"  Skills: {re.extracted_skills}")
            print(f"  Summary: {re.summary[:100] if re.summary else 'None'}")
            print(f"  Match %: {re.skill_match_percentage}")
        else:
            print("  NO EXTRACTION FOUND")
        print("-" * 20)
finally:
    db.close()
