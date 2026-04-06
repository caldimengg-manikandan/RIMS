import os
import sys
sys.path.append(os.getcwd())
from app.infrastructure.database import SessionLocal
from app.domain.models import Application
db = SessionLocal()
apps = db.query(Application).all()
print(f"Total Applications: {len(apps)}")
for app in apps:
    e = app.candidate_email.lower()
    if 'ozsaip' in e or 'oil' in e or 'oii' in e:
        print(f"{app.id}: {app.candidate_email}")
db.close()
