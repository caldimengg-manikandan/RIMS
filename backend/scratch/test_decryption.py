import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.core.encryption import decrypt_field
from app.domain.models import AuditLog
from app.infrastructure.database import SessionLocal

def test_decryption():
    db = SessionLocal()
    try:
        # Get the 10 most recent logs with details
        logs = db.query(AuditLog).filter(AuditLog.details.isnot(None)).order_by(AuditLog.id.desc()).all()
        
        print(f"Testing decryption of {len(logs)} logs...\n")
        
        success_count = 0
        fail_count = 0
        
        for log in logs:
            try:
                # Decrypting details
                decrypted = decrypt_field(log.details)
                if decrypted == "[DECRYPTION_ERROR]":
                     fail_count += 1
                     # print(f"Log #{log.id}: FAILED - Invalid Token")
                else:
                     success_count += 1
                     # print(f"Log #{log.id}: SUCCESS - {decrypted[:50]}...")
            except Exception as e:
                fail_count += 1
                # print(f"Log #{log.id}: FAILED - {str(e)}")
        
        print(f"\nFinal Results:")
        print(f"Total Logs with details: {len(logs)}")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")
                
    finally:
        db.close()

if __name__ == "__main__":
    test_decryption()
