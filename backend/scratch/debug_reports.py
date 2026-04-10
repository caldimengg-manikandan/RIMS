from app.infrastructure.database import SessionLocal
from app.domain.models import Interview, Application, InterviewReport

db = SessionLocal()
try:
    interviews = db.query(Interview).all()
    print(f"Total Interviews: {len(interviews)}")
    for i in interviews:
        app_status = i.application.status if i.application else "N/A"
        rep_exists = i.report is not None
        print(f"ID: {i.id}, Status: {i.status}, App Status: {app_status}, Report: {rep_exists}")

    apps = db.query(Application).filter(Application.status.in_(["review_later", "hired", "rejected", "interview_completed"])).all()
    print(f"\nCandidates in target statuses: {len(apps)}")
    for a in apps:
        print(f"App ID: {a.id}, Status: {a.status}, Interview Status: {a.interview.status if a.interview else 'No Interview'}")

finally:
    db.close()
