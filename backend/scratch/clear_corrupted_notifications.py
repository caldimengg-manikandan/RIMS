import sys
import os

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.infrastructure.database import SessionLocal
from app.domain.models import Notification
from app.core.encryption import decrypt_field

def clear_corrupted_notifications():
    db = SessionLocal()
    try:
        print("Fetching all notifications...")
        notifications = db.query(Notification).all()
        count = 0
        deleted_count = 0
        
        for n in notifications:
            count += 1
            # Try to decrypt the message
            decrypted = decrypt_field(n.message)
            if decrypted == "[DECRYPTION_ERROR]":
                print(f"Found corrupted notification (ID: {n.id}). Deleting...")
                db.delete(n)
                deleted_count += 1
        
        if deleted_count > 0:
            db.commit()
            print(f"Successfully deleted {deleted_count} corrupted notifications out of {count} total.")
        else:
            print(f"No corrupted notifications found out of {count} total.")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_corrupted_notifications()
