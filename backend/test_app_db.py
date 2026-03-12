import asyncio
from app.infrastructure.database import SessionLocal
from app.domain.models import User

def test_db():
    print("Initiating DB session...")
    db = SessionLocal()
    try:
        print("Executing query...")
        users = db.query(User).all()
        print(f"Success! Found {len(users)} users.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        print("Finished.")

if __name__ == "__main__":
    test_db()
