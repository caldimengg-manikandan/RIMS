import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Add current dir to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.database import SessionLocal
from app.domain.models import Application, AuditLog, GlobalSettings

def run_retention_cleanup():
    """Point 5: Data Retention Policy Implementation."""
    db = SessionLocal()
    try:
        # 1. Fetch retention policy from Settings (default 365 days)
        retention_days_setting = db.query(GlobalSettings).filter(GlobalSettings.key == "retention_days").first()
        days = int(retention_days_setting.value) if retention_days_setting else 365
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        print(f"Cleaning up records older than {cutoff_date} ({days} days)...")

        # 2. Anonymize/Cleanup old offer data in Applications
        old_apps = db.query(Application).filter(Application.applied_at < cutoff_date).all()
        for app in old_apps:
            # Anonymize PII
            app.offer_accepted_ip = "[ANONYMIZED]"
            app.offer_accepted_user_agent = "[ANONYMIZED]"
            
            # Delete physical PDF if exists
            if app.offer_pdf_path and os.path.exists(app.offer_pdf_path):
                try:
                    os.remove(app.offer_pdf_path)
                    print(f"Deleted PDF: {app.offer_pdf_path}")
                except Exception as e:
                    print(f"Failed to delete file {app.offer_pdf_path}: {e}")
            
            app.offer_pdf_path = None
        
        # 3. Cleanup Audit Logs IP
        old_logs = db.query(AuditLog).filter(AuditLog.created_at < cutoff_date).all()
        for log in old_logs:
            log.ip_address = "[PURGED]"

        db.commit()
        print(f"Retention cleanup complete. Processed {len(old_apps)} applications and {len(old_logs)} audit logs.")

    except Exception as e:
        print(f"Cleanup Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_retention_cleanup()
