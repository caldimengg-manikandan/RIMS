with open(r'C:\Users\user\Desktop\PROJECT\rims\backend\app\main.py', 'a', encoding='utf-8') as f:
    f.write('''\n
import asyncio
from app.services.email_ingestion_service import fetch_resume_attachments
from app.infrastructure.database import SessionLocal
import os

async def imap_polling_loop():
    while True:
        try:
            db = SessionLocal()
            # Fetch automatically
            fetch_resume_attachments(db, 'caldiminternship@gmail.com', 'jaesbucnsfnlediv')
            db.close()
        except Exception as e:
            logger.error(f"IMAP Polling Error: {e}")
        
        # Sleep for 60 seconds (1 minute) to avoid getting blocked by Google IMAP limits.
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    # Start the continuous email ingestion loop
    asyncio.create_task(imap_polling_loop())
''')
