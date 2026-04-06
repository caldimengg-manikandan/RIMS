import os
import sys
# Add current directory to path
sys.path.append(os.getcwd())

from app.infrastructure.database import SessionLocal
from app.domain.models import Application, Interview
from app.core.auth import pwd_context

db = SessionLocal()
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--email", default="Oii2n8r3qk@ozsaip.com")
parser.add_argument("--key", default="h6zARJn-Op6K9gA1SrvcUQ")
args = parser.parse_args()

email = args.email
key = args.key

print(f"Checking access for Email: {email}")
app = db.query(Application).filter(Application.candidate_email == email).first()

if not app:
    print(f"ERROR: Candidate email {email} not found in applications table.")
else:
    print(f"Found Application ID: {app.id}")
    interviews = db.query(Interview).filter(Interview.application_id == app.id).all()
    if not interviews:
        print("ERROR: No interviews found for this application.")
    else:
        for inv in interviews:
            print(f"-- Interview ID: {inv.id} --")
            print(f"   Status: {inv.status}")
            print(f"   Is Used: {inv.is_used}")
            print(f"   Expires At: {inv.expires_at}")
            print(f"   Key Hash: {inv.access_key_hash}")
            
            try:
                is_valid = pwd_context.verify(key, inv.access_key_hash)
                print(f"   Key Verification Result: {'VALID' if is_valid else 'INVALID'}")
            except Exception as e:
                print(f"   Key Verification Error: {e}")

db.close()
