from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.domain.models import User, Job, Application
from app.domain.schemas import JobCreate, JobUpdate, JobResponse, JobExtractionResponse
from app.core.auth import get_current_user, get_current_hr
from app.services.ai_service import extract_job_details
from app.services.resume_parser import parse_resume
from app.core.config import get_settings
import json
import os
import uuid
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
settings = get_settings()

VALID_INTERVIEW_MODES = {"ai", "upload", "mixed"}
ALLOWED_QUESTION_EXTENSIONS = {".txt", ".pdf", ".docx"}
ALLOWED_APTITUDE_EXTENSIONS = {".txt", ".pdf", ".docx"}
MAX_QUESTION_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def generate_unique_job_id(db: Session) -> str:
    """Generate a unique job ID in the format JOB-XXXXXX"""
    while True:
        import random
        import string
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        job_id = f"JOB-{suffix}"
        
        # Check if already exists
        exists = db.query(Job).filter(Job.job_id == job_id).first()
        if not exists:
            return job_id


def _validate_interview_pipeline(job_data, experience_level: str):
    """
    Validate interview pipeline fields and return sanitized values.
    Raises HTTPException(400) on invalid combinations.
    """
    aptitude_enabled = getattr(job_data, 'aptitude_enabled', False) or False
    first_level_enabled = getattr(job_data, 'first_level_enabled', False) or False
    interview_mode = getattr(job_data, 'interview_mode', None)
    uploaded_question_file = getattr(job_data, 'uploaded_question_file', None)
    aptitude_config = getattr(job_data, 'aptitude_config', None)

    # Rule 1: aptitude_enabled only allowed for junior
    if aptitude_enabled and experience_level != "junior":
        raise HTTPException(
            status_code=400,
            detail="Aptitude round is only available for Junior (0-2 years) experience level."
        )

    # Rule 2: If first_level_enabled, interview_mode must be valid
    if first_level_enabled:
        if interview_mode not in VALID_INTERVIEW_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"When First Level Interview is enabled, interview_mode must be one of: {', '.join(VALID_INTERVIEW_MODES)}."
            )
    else:
        # Rule 3: If first_level disabled, force nulls
        interview_mode = None
        uploaded_question_file = None

    # Rule 4: If mode is AI only, clear the file (Upload and Mixed modes retain uploaded files)
    if interview_mode == "ai":
        uploaded_question_file = None

    # Rule 5: If mode is upload, file is required
    if interview_mode == "upload" and not uploaded_question_file:
        raise HTTPException(
            status_code=400,
            detail="When interview mode is 'upload', a question file must be uploaded first."
        )

    return {
        "aptitude_enabled": aptitude_enabled,
        "first_level_enabled": first_level_enabled,
        "interview_mode": interview_mode,
        "uploaded_question_file": uploaded_question_file,
        "aptitude_config": aptitude_config,
        "aptitude_questions_file": getattr(job_data, 'aptitude_questions_file', None),
        "aptitude_mode": getattr(job_data, 'aptitude_mode', "ai"),
        "behavioral_role": getattr(job_data, 'behavioral_role', "general"),
    }


@router.post("/upload-questions")
async def upload_question_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_hr),
):
    """Upload a question file (.txt, .pdf, .docx). Returns the stored file path."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_QUESTION_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_QUESTION_EXTENSIONS)}"
        )

    # Validate file size (read content to check)
    content = await file.read()
    if len(content) > MAX_QUESTION_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_QUESTION_FILE_SIZE // (1024*1024)}MB."
        )

    # Sanitize filename: use UUID to prevent path traversal and collisions
    safe_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = settings.base_dir / "uploads" / "questions"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(content)

    # Return path relative to the backend dir for storage
    relative_path = f"uploads/questions/{safe_name}"
    return {"file_path": relative_path, "original_name": file.filename}


@router.post("/upload-aptitude-questions")
async def upload_aptitude_questions(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_hr)
):
    """
    Upload an Excel (.xlsx) file containing aptitude questions.
    Expects columns: 'Question', 'Answer', and optionally 'Options'
    """
    # Accept excel files
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    filename = file.filename.lower()
    ext = os.path.splitext(filename)[1]
    
    # We only accept excel mode for the new spec
    if ext not in [".xlsx", ".xls"]:
         raise HTTPException(status_code=400, detail="Only Excel (.xlsx/.xls) files are accepted.")
    
    content = await file.read()
    if len(content) > MAX_QUESTION_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_QUESTION_FILE_SIZE // (1024*1024)}MB."
        )
    try:
        import pandas as pd
        import io
        
        df = pd.read_excel(io.BytesIO(content))
        
        # Validate columns
        required_cols = ['Question', 'Answer']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
             raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}\nFound columns: {list(df.columns)}")
        
        questions = []
        for index, row in df.iterrows():
            q_text = str(row['Question']).strip()
            answer = str(row['Answer']).strip()
            
            if not q_text or q_text == 'nan':
                 continue
                 
            q_dict = {
                "question": q_text,
                "answer": answer
            }
            if 'Options' in df.columns and pd.notna(row['Options']):
                 q_dict["options"] = [opt.strip() for opt in str(row['Options']).split(',') if opt.strip()]
                 
            questions.append(q_dict)
            
    except Exception as e:
        if isinstance(e, HTTPException):
             raise e
        raise HTTPException(status_code=400, detail=f"Could not parse Excel file: {str(e)}")

    if len(questions) < 1:
        raise HTTPException(
            status_code=400,
            detail="No valid questions found in the uploaded file."
        )

    # Save as JSON for _generate_aptitude_questions to consume
    safe_name = f"{uuid.uuid4().hex}.json"
    upload_dir = settings.base_dir / "uploads" / "aptitude_questions"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / safe_name
    import json as json_mod
    with open(file_path, "w", encoding="utf-8") as f:
        json_mod.dump(questions, f, ensure_ascii=False, indent=2)

    relative_path = f"uploads/aptitude_questions/{safe_name}"
    return {
        "file_path": relative_path,
        "original_name": file.filename,
        "questions_count": len(questions),
    }


@router.post("/extract", response_model=JobExtractionResponse)
async def extract_job(
    text_content: str = Form(None),
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_hr)
):
    """Extract job details from text or PDF using AI"""
    content = ""
    
    if file and file.filename:
        content = parse_resume(file)
    elif text_content:
        content = text_content
        
    if not content or len(content.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide job description text or upload a valid file.")
        
    extracted_data = await extract_job_details(content)
    return extracted_data

@router.post("", response_model=JobResponse)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Create a new job posting (HR only)"""
    # Validate interview pipeline
    pipeline = _validate_interview_pipeline(job_data, job_data.experience_level)
    
    # Generate unique Job ID
    job_identifier = generate_unique_job_id(db)

    new_job = Job(
        job_id=job_identifier,
        interview_token=uuid.uuid4().hex,
        title=job_data.title,
        description=job_data.description,
        experience_level=job_data.experience_level,
        hr_id=current_user.id,
        location=job_data.location,
        mode_of_work=job_data.mode_of_work,
        job_type=job_data.job_type,
        domain=job_data.domain,
        primary_evaluated_skills=json.dumps(job_data.primary_evaluated_skills) if job_data.primary_evaluated_skills else None,
        # Interview pipeline
        aptitude_enabled=pipeline["aptitude_enabled"],
        aptitude_mode=pipeline.get("aptitude_mode", "ai"),
        first_level_enabled=pipeline["first_level_enabled"],
        interview_mode=pipeline["interview_mode"],
        behavioral_role=pipeline.get("behavioral_role", "general"),
        uploaded_question_file=pipeline["uploaded_question_file"],
        aptitude_config=pipeline["aptitude_config"],
        aptitude_questions_file=pipeline["aptitude_questions_file"],
    )
    
    try:
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        return new_job
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create job safely")

@router.get("/public", response_model=list[JobResponse])
def list_public_jobs(
    db: Session = Depends(get_db)
):
    """List all open and closed jobs (Public endpoint)"""
    jobs = db.query(Job).filter(Job.status.in_(["open", "closed"])).all()
    return jobs

@router.get("", response_model=list[JobResponse])
def list_jobs(
    status: str = None,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """List all jobs for the HR user"""
    query = db.query(Job)
    
    # Apply optional status filter
    if status:
        query = query.filter(Job.status == status)
    
    jobs = query.all()
    return jobs

@router.get("/public/{job_id}", response_model=JobResponse)
def get_public_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get open/closed job details (Public endpoint)"""
    job = db.query(Job).filter(Job.id == job_id, Job.status.in_(["open", "closed"])).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not open/closed"
        )
    
    return job

@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get job details (HR only)"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    
    return job

@router.put("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Update job (HR only)"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    
    # Update standard fields
    if job_data.title:
        job.title = job_data.title
    if job_data.description:
        job.description = job_data.description
    if job_data.experience_level:
        job.experience_level = job_data.experience_level
    if job_data.location:
        job.location = job_data.location
    if job_data.mode_of_work:
        job.mode_of_work = job_data.mode_of_work
    if job_data.job_type:
        job.job_type = job_data.job_type
    if job_data.domain:
        job.domain = job_data.domain
    if job_data.status:
        if job_data.status == "closed" and job.status != "closed":
            job.closed_at = datetime.utcnow()
        elif job_data.status != "closed":
            job.closed_at = None
        job.status = job_data.status
    if job_data.primary_evaluated_skills is not None:
        job.primary_evaluated_skills = json.dumps(job_data.primary_evaluated_skills)
    
    # Update interview pipeline fields if ANY pipeline field was sent
    pipeline_fields_sent = any([
        job_data.aptitude_enabled is not None,
        job_data.first_level_enabled is not None,
        job_data.interview_mode is not None,
        job_data.uploaded_question_file is not None,
        job_data.aptitude_config is not None,
    ])

    if pipeline_fields_sent:
        # Resolve effective experience level (could be changing in same request)
        effective_exp = job_data.experience_level or job.experience_level

        # Build a combined state using new values where provided, old values as fallback
        class _Combined:
            aptitude_enabled = job_data.aptitude_enabled if job_data.aptitude_enabled is not None else job.aptitude_enabled
            first_level_enabled = job_data.first_level_enabled if job_data.first_level_enabled is not None else job.first_level_enabled
            interview_mode = job_data.interview_mode if job_data.interview_mode is not None else job.interview_mode
            uploaded_question_file = job_data.uploaded_question_file if job_data.uploaded_question_file is not None else job.uploaded_question_file
            aptitude_config = job_data.aptitude_config

        pipeline = _validate_interview_pipeline(_Combined(), effective_exp)
        job.aptitude_enabled = pipeline["aptitude_enabled"]
        job.first_level_enabled = pipeline["first_level_enabled"]
        job.interview_mode = pipeline["interview_mode"]
        job.uploaded_question_file = pipeline["uploaded_question_file"]
        if pipeline["aptitude_config"] is not None:
            job.aptitude_config = pipeline["aptitude_config"]
        if pipeline["aptitude_questions_file"] is not None:
            job.aptitude_questions_file = pipeline["aptitude_questions_file"]

    try:
        db.commit()
        db.refresh(job)
        return job
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update job safely")

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Delete/Close job (HR only)"""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    
    # Delete the job (and associated data manually to ensure cascade)
    try:
        # Fetch all applications for this job
        applications = db.query(Application).filter(Application.job_id == job_id).all()
        
        for app in applications:
            # Delete related data for each application
            # Interviews
            if app.interview:
                # Delete interview questions and answers (if cascade doesn't handle it)
                for question in app.interview.questions:
                    for answer in question.answers:
                        db.delete(answer)
                    db.delete(question)
                if app.interview.report:
                    db.delete(app.interview.report)
                db.delete(app.interview)
            
            # Resume Extraction
            if app.resume_extraction:
                db.delete(app.resume_extraction)
                
            # Hiring Decision
            if app.hiring_decision:
                db.delete(app.hiring_decision)
            
            # Finally delete the application
            db.delete(app)
            
        # Clean up uploaded files from disk
        for file_field in [job.aptitude_questions_file, job.uploaded_question_file]:
            if file_field:
                try:
                    file_path = settings.base_dir / file_field
                    if file_path.exists():
                        file_path.unlink()
                except Exception as cleanup_err:
                    print(f"Warning: Failed to clean up file {file_field}: {cleanup_err}")

        # Delete the job
        db.delete(job)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error deleting job: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )
    return None
