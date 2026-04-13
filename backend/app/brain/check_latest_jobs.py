import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    res = conn.execute(text('SELECT id, job_id, title, hr_id, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10'))
    print("Latest Jobs:")
    for r in res:
        print(f"ID: {r.id}, JobID: {r.job_id}, Title: {r.title}, HR_ID: {r.hr_id}, Status: {r.status}, CreatedAt: {r.created_at}")
