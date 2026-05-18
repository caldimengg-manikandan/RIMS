import sys
import os
sys.path.append(os.getcwd())

from app.infrastructure.database import SessionLocal
from app.domain.models import Application

db = SessionLocal()
try:
    # Update candidate_1@example.com to use the test domain
    app = db.query(Application).filter(Application.candidate_email == "candidate_1@example.com").first()
    if app:
        app.candidate_email = "kvfpru233c@gmeenramy.com"
        db.commit()
        print(f"Updated candidate_1 email to: {app.candidate_email}")
    else:
        print("candidate_1@example.com not found!")
finally:
    db.close()
