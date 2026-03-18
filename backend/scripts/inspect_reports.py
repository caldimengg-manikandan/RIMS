import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.domain.models import InterviewReport

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

def inspect_reports():
    reports = db.query(InterviewReport).all()
    print(f"Total Reports in DB: {len(reports)}")
    for r in reports:
        print(f"Report ID: {r.id}, IntId: {r.interview_id}, Score: {r.overall_score}, Status: {r.conclusion if hasattr(r, 'conclusion') else 'N/A'}")

if __name__ == "__main__":
    inspect_reports()
