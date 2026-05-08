from app.infrastructure.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            # Shift all applied_at by 5 hours 30 minutes to convert UTC storage to IST storage
            print("Running migration...")
            conn.execute(text("UPDATE applications SET applied_at = applied_at + interval '5 hours 30 minutes'"))
            conn.commit()
            print("Migration OK: applied_at shifted to IST.")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
