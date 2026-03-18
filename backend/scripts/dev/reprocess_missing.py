
import asyncio
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Setup DB
DATABASE_URL = "mysql+pymysql://root:0000@localhost/rims_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Path setup - match config.py logic
BASE_DIR = Path(__file__).resolve().parent / "app"
UPLOAD_DIR = BASE_DIR / "uploads" / "resumes"

async def reprocess_missing():
    from app.domain.models import Application, ResumeExtraction, Job
    from app.services.ai_service import parse_resume_with_ai
    
    db = SessionLocal()
    try:
        # Find applications with missing extractions
        apps = db.query(Application).filter(~Application.id.in_(db.query(ResumeExtraction.application_id))).all()
        print(f"Found {len(apps)} applications missing resume extractions.")
        
        for app in apps:
            print(f"Processing App {app.id} ({app.candidate_name})...")
            
            # Construct absolute path
            # resume_file_path is like 'uploads/resumes/filename.pdf'
            filename = os.path.basename(app.resume_file_path)
            abs_file_path = UPLOAD_DIR / filename
            
            if not abs_file_path.exists():
                print(f"  [Error] Physical file not found at {abs_file_path}")
                continue
                
            # Extract text
            resume_text = ""
            file_ext = filename.lower().split('.')[-1]
            try:
                if file_ext == 'pdf':
                    from pypdf import PdfReader
                    reader = PdfReader(abs_file_path)
                    for page in reader.pages:
                        resume_text += page.extract_text() + "\n"
                elif file_ext in ['docx', 'doc']:
                    import docx
                    doc = docx.Document(abs_file_path)
                    for para in doc.paragraphs:
                        resume_text += para.text + "\n"
                else:
                    with open(abs_file_path, "rb") as f:
                        resume_text = f.read().decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"  [Error] Text extraction failed: {e}")
                continue

            if not resume_text.strip():
                resume_text = "No readable text found."

            # AI Parsing
            job = db.query(Job).filter(Job.id == app.job_id).first()
            extraction_data = await parse_resume_with_ai(resume_text, app.job_id, job.description if job else "")
            
            # Store extraction
            re = ResumeExtraction(
                application_id=app.id,
                extracted_text=resume_text,
                summary=extraction_data.get("summary", ""),
                extracted_skills=json.dumps(extraction_data.get("skills") or []),
                years_of_experience=extraction_data.get("experience"),
                education=json.dumps(extraction_data.get("education") or []),
                previous_roles=json.dumps(extraction_data.get("roles") or []),
                experience_level=extraction_data.get("experience_level"),
                resume_score=extraction_data.get("score", 0),
                skill_match_percentage=extraction_data.get("match_percentage", 0)
            )
            db.add(re)
            app.resume_score = extraction_data.get("score", 0)
            db.commit()
            print(f"  [Success] Saved extraction for {app.candidate_name}")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(reprocess_missing())
