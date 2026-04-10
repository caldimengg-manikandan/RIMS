from sqlalchemy import create_engine, text
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.config import get_settings

def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("Applying migration to and interview_issues...")
        try:
            # PostgreSQL syntax
            conn.execute(text("ALTER TABLE interview_issues ALTER COLUMN interview_id DROP NOT NULL;"))
            conn.execute(text("ALTER TABLE interview_issues ADD COLUMN IF NOT EXISTS application_id INTEGER REFERENCES applications(id);"))
            conn.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
