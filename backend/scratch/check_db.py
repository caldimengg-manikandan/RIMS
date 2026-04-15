
from app.infrastructure.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    res = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'question_sets'"))
    cols = [r[0] for r in res]
    print(f"Columns: {cols}")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
