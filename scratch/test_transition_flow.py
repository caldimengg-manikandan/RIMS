import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import timedelta

# Load env
load_dotenv('backend/.env')

db_url = os.environ.get("DATABASE_URL")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

from app.domain.models import Application, User, Job
from app.services.state_machine import CandidateStateMachine, TransitionAction, CandidateState
from app.core.timezone import get_ist_now
import uuid

# Find HR user and job
hr = session.query(User).filter(User.role == "hr").first()
job = session.query(Job).first()

# Create dummy application
app = Application(
    candidate_name="Test Transitions User",
    candidate_email="transition_user@test.com",
    status="hired",
    hr_id=hr.id,
    job_id=job.id,
    joining_date=get_ist_now() + timedelta(days=3),
    offer_token=str(uuid.uuid4())
)
session.add(app)
session.commit()

print(f"Created application: {app.id}")
print(f"Initial status: {app.status}")

# Transition to pending_approval
fsm = CandidateStateMachine(session)
fsm.transition(app, TransitionAction.SEND_FOR_APPROVAL, user_id=hr.id)
session.commit()
print(f"Status after SEND_FOR_APPROVAL: {app.status}")

# Transition to offer_sent
fsm.transition(app, TransitionAction.SEND_OFFER, user_id=hr.id)
session.commit()
print(f"Status after SEND_OFFER: {app.status}")
print(f"Offer token used: {app.offer_token_used}, Response status: {app.offer_response_status}")

# Candidate responds accept
fsm.transition(app, TransitionAction.ACCEPT_OFFER)
app.offer_token_used = True
app.offer_response_status = "accept"
session.commit()
print(f"Status after ACCEPT_OFFER: {app.status}")
print(f"Offer token used: {app.offer_token_used}, Response status: {app.offer_response_status}")

# Cleanup
session.delete(app)
session.commit()
print("Cleaned up successfully.")
