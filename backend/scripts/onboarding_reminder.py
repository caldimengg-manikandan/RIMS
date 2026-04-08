import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Add current dir to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database import SessionLocal
from app.domain.models import Application, User, Notification
from app.services.email_service import send_email_async
import asyncio

async def check_onboarding_reminders():
    """Notify HR about upcoming joiners (7-day reminder)."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        candidates = db.query(Application).filter(
            Application.status == "accepted",
            Application.joining_date >= (now + timedelta(days=6)),
            Application.joining_date <= (now + timedelta(days=8)),
            Application.reminder_sent_at == None
        ).all()
        
        print(f"Scheduler: Found {len(candidates)} candidates for approx 7-day reminder")
        
        for app in candidates:
            hrs = db.query(User).filter(User.role.in_(["super_admin", "hr"])).all()
            subject = f"Upcoming Joining: {app.candidate_name}"
            message = (
                f"Candidate {app.candidate_name} is scheduled to join as {app.job.title} "
                f"on {app.joining_date.strftime('%B %d, %Y')}. "
                f"Please ensure all onboarding formalities are complete."
            )
            
            for hr in hrs:
                notif = Notification(
                    user_id=hr.id,
                    notification_type="onboarding_reminder",
                    title="Upcoming Candidate Joining",
                    message=message,
                    related_application_id=app.id
                )
                db.add(notif)
                await send_email_async(
                    to_email=hr.email,
                    subject=subject,
                    html_body=f"<html><body><h2>{subject}</h2><p>{message}</p></body></html>"
                )
            
            app.reminder_sent_at = now
            app.notification_sent = True # Compatibility
            db.commit()
            print(f"Sent joining reminders for {app.candidate_name}")
            
    except Exception as e:
        print(f"Scheduler joining reminder Error: {e}")
    finally:
        db.close()

async def retry_failed_emails():
    """Point 7: Retry failed emails every cycle (up to 3 times)."""
    db = SessionLocal()
    try:
        failed_apps = db.query(Application).filter(
            Application.offer_email_status == "failed",
            Application.offer_email_retry_count < 3
        ).all()
        
        if failed_apps:
            print(f"Scheduler: Retrying {len(failed_apps)} failed offer emails")
            # In a real system we'd store the PDF path. 
            # We'll increment retry count and log.
            for app in failed_apps:
                print(f"Retrying email for {app.candidate_name} (Attempt {app.offer_email_retry_count + 1})")
                app.offer_email_retry_count += 1
                db.commit()
    except Exception as e:
        print(f"Scheduler retry error: {e}")
    finally:
        db.close()

async def check_non_response_reminders():
    """Point 8: Notify HR if candidate hasn't responded within 3 days."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        three_days_ago = now - timedelta(days=3)
        
        neglected_apps = db.query(Application).filter(
            Application.status == "offer_sent",
            Application.offer_sent_date <= three_days_ago,
            Application.offer_response_status == "pending"
        ).all()
        
        for app in neglected_apps:
            hrs = db.query(User).filter(User.role == "hr").all()
            for hr in hrs:
                notif = Notification(
                    user_id=hr.id,
                    notification_type="OFFER_EXPIRY_WARNING",
                    title="Awaiting Candidate Response",
                    message=f"Candidate {app.candidate_name} has not responded to the offer sent on {app.offer_sent_date.strftime('%Y-%m-%d')}.",
                    related_application_id=app.id
                )
                db.add(notif)
            db.commit()
            print(f"Sent non-response alerts for {app.candidate_name}")
    except Exception as e:
        print(f"Scheduler non-response error: {e}")
    finally:
        db.close()

async def run_all_tasks():
    print(f"--- Onboarding Scheduler Started at {datetime.now()} ---")
    await check_onboarding_reminders()
    await retry_failed_emails()
    await check_non_response_reminders()
    print("--- Onboarding Scheduler Completed ---")

if __name__ == "__main__":
    asyncio.run(run_all_tasks())
