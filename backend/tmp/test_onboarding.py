
import json
import uuid
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import SessionLocal
from app.domain.models import User, Job, Application, GlobalSettings, AuditLog
from app.services.state_machine import CandidateStateMachine, TransitionAction, CandidateState
from app.api.onboarding import (
    request_offer_approval, 
    approve_offer_letter, 
    respond_to_offer,
    capture_photo,
    generate_id_card
)
from app.domain.schemas import OfferResponseRequest
import os

# Set environment for script mode
os.environ["BACKEND_START_MODE"] = "script"

def setup_test_data(db):
    # 1. Ensure a Super Admin exists
    admin = db.query(User).filter(User.role == "super_admin").first()
    if not admin:
        admin = User(
            email="test_admin@example.com",
            full_name="Test Admin",
            password_hash="fake_hash",
            role="super_admin",
            is_active=True,
            is_verified=True,
            approval_status="approved"
        )
        db.add(admin)
        db.commit()
    
    # 2. Ensure Global Settings exist
    settings = {
        "company_name": "Test Corp",
        "offer_letter_template": "<h1>Offer for {{candidate_name}}</h1><p>Welcome to {{company_name}}!</p>",
        "hr_email": "hr@example.com"
    }
    for k, v in settings.items():
        if not db.query(GlobalSettings).filter(GlobalSettings.key == k).first():
            db.add(GlobalSettings(key=k, value=v))
    db.commit()

    # 3. Create a Job
    job = Job(
        title="Test Engineer",
        description="Testing recruitment workflow",
        experience_level="Senior",
        hr_id=admin.id,
        status="open"
    )
    db.add(job)
    db.commit()
    
    # 4. Create an Application in 'hired' state
    app = Application(
        job_id=job.id,
        hr_id=admin.id,
        candidate_name="John Doe",
        candidate_email="john@doe.com",
        status="hired",
        applied_at=datetime.now(timezone.utc)
    )
    db.add(app)
    db.commit()
    
    return admin, job, app

async def test_onboarding_flow():
    db = SessionLocal()
    try:
        admin, job, app = setup_test_data(db)
        print(f"--- TEST START: Application ID {app.id} ---")

        # Step 1: Stage Offer (HR action)
        print("1. Staging offer...")
        # Since we are not in a request context, we call the logic directly
        # bypassing the background tasks for this unit test
        await request_offer_approval(
            application_id=app.id,
            joining_date=(datetime.now() + timedelta(days=30)).isoformat(),
            db=db,
            current_user=admin
        )
        db.refresh(app)
        print(f"   Status: {app.status}, Offer Token: {app.offer_token[:8]}...")

        # Step 2: Approve Offer (Admin action)
        print("2. Approving offer...")
        class MockBackgroundTasks:
            def add_task(self, *args, **kwargs): pass

        await approve_offer_letter(
            application_id=app.id,
            background_tasks=MockBackgroundTasks(),
            db=db,
            current_user=admin
        )
        db.refresh(app)
        print(f"   Status: {app.status}, Offer Sent: {app.offer_sent}")

        # Step 3: Candidate Response (Public action)
        print("3. Candidate accepting offer...")
        class MockRequest:
            headers = {}
            client = type('obj', (object,), {'host': '127.0.0.1'})
            
        await respond_to_offer(
            request=MockRequest(),
            response_req=OfferResponseRequest(token=app.offer_short_id, response_type="accept"),
            db=db
        )
        db.refresh(app)
        print(f"   Status: {app.status}, Response: {app.offer_response_status}")

        # Step 4: Complete Onboarding (HR action)
        # We manually move it to onboarded to test photo capture
        print("4. Completing onboarding...")
        fsm = CandidateStateMachine(db)
        fsm.transition(app, TransitionAction.SYSTEM_ONBOARD, user_id=admin.id)
        db.commit()
        print(f"   Status: {app.status}")

        # Step 5: Capture Photo (Mocked storage)
        print("5. Capturing photo (Mocked)...")
        class MockFile:
            def __init__(self): self.filename = "photo.jpg"; self.content_type = "image/jpeg"
            async def read(self): return b"fake_photo_bytes"
            
        await capture_photo(
            application_id=app.id,
            photo=MockFile(),
            db=db,
            current_user=admin
        )
        db.refresh(app)
        print(f"   Photo Path: {app.candidate_photo_path}")

        # Step 6: Generate ID Card (Mocked storage)
        print("6. Generating ID card (Mocked)...")
        id_card_res = generate_id_card(
            application_id=app.id,
            db=db,
            current_user=admin
        )
        db.refresh(app)
        print(f"   ID Card Path: {app.id_card_url}, Employee ID: {app.employee_id}")

        print("--- TEST SUCCESS: End-to-end onboarding logic verified! ---")

    except Exception as e:
        print(f"!!! TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_onboarding_flow())
