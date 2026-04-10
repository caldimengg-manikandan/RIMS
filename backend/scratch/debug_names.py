from app.infrastructure.database import SessionLocal
from app.domain.models import Interview, Application

db = SessionLocal()
try:
    i120 = db.query(Interview).filter(Interview.id == 120).first()
    print(f"ID 120: Name={i120.application.candidate_name if i120.application else 'N/A'}")
    
    i129 = db.query(Interview).filter(Interview.id == 129).first()
    print(f"ID 129: Name={i129.application.candidate_name if i129.application else 'N/A'}")

finally:
    db.close()
