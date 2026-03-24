
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from pathlib import Path

# Load env from backend/.env
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Aborting.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    from app.domain.models import Application
    app = db.query(Application).filter(Application.id == 5).first()
    if app:
        print(f"File Path: {app.resume_file_path}")
        abs_path = os.path.join(r"c:\R\RIMS\backend", app.resume_file_path.replace("/", "\\"))
        print(f"Abs Path: {abs_path}")
        if os.path.exists(abs_path):
            print(f"Size: {os.path.getsize(abs_path)} bytes")
            # Try to extract text
            from pypdf import PdfReader
            reader = PdfReader(abs_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            print(f"Extracted Text Length: {len(text)}")
            print(f"Sample: {text[:200]}")
        else:
            print("FILE DOES NOT EXIST")
finally:
    db.close()
