from app.infrastructure.database import SessionLocal
from app.domain.models import Interview, Application, User

db = SessionLocal()
try:
    hrs = db.query(User).filter(User.role == "hr").all()
    print(f"Total HRs: {len(hrs)}")
    for hr in hrs:
        print(f"HR ID: {hr.id}, Email: {hr.email}")

    interviews = db.query(Interview).all()
    print(f"\nTotal Interviews: {len(interviews)}")
    for i in interviews:
        hr_id = i.application.hr_id if i.application else "N/A"
        print(f"ID: {i.id}, Status: {i.status}, App Status: {i.application.status if i.application else 'N/A'}, HR ID: {hr_id}")

finally:
    db.close()
