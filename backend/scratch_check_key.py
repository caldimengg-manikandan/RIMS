import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database import SessionLocal
from app.domain.models import Application, Interview

def check():
    db = SessionLocal()
    try:
        a = db.query(Application).filter(Application.id == 749).first()
        if not a:
            print("Application 749 not found!")
            return
        
        print("Application attributes:")
        for attr in sorted(a.__dict__.keys()):
            if not attr.startswith('_'):
                print(f"  {attr}: {a.__dict__[attr]}")
        
        i = db.query(Interview).filter(Interview.application_id == 749).first()
        if i:
            print("\nInterview attributes:")
            for attr in sorted(i.__dict__.keys()):
                if not attr.startswith('_'):
                    print(f"  {attr}: {i.__dict__[attr]}")
        else:
            print("No Interview found for 749!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
