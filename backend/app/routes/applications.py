from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session, joinedload
import os
import json
from datetime import datetime, timezone
from app.database import get_db
from app.models import User, Application, Job, ResumeExtraction, Interview, InterviewAnswer
from app.schemas import ApplicationCreate, ApplicationStatusUpdate, ApplicationResponse, ApplicationDetailResponse
from app.auth import get_current_user, get_current_hr
from app.services.ai_service import parse_resume_with_ai
from app.services.email_service import send_application_received_email, send_rejected_email, send_approved_for_interview_email
import secrets
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from app.config import get_settings
settings = get_settings()

UPLOAD_DIR = settings.uploads_dir / "resumes"
PHOTO_DIR = settings.uploads_dir / "photos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PHOTO_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/applications", tags=["applications"])

@router.post("/apply", response_model=ApplicationResponse)
async def apply_for_job(
    job_id: int = Form(...),
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    candidate_phone: str = Form(None),
    resume_file: UploadFile = File(...),
    photo_file: UploadFile = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Apply for a job with resume (Public endpoint)"""
    # Check if job exists and is open
    job = db.query(Job).filter(Job.id == job_id, Job.status == "open").first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not open"
        )
    
    # Check if already applied
    # Check if already applied
    candidate_email = candidate_email.lower().strip()
    existing_app = db.query(Application).filter(
        Application.job_id == job_id,
        Application.candidate_email == candidate_email
    ).first()
    
    if existing_app:
        # If the previous application was rejected, allow re-application by deleting the old one
        if existing_app.status == "rejected":
            try:
                # Start fresh - delete the old application tree (cascades should handle relations)
                db.delete(existing_app)
                db.commit()
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Failed to recycle rejected application securely")
            # Loop continues to create new app
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already applied for this job"
            )
    
    MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB
    ALLOWED_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
    
    # Validate file content type
    if resume_file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and DOCX allowed."
        )
        
    # Validate file size (Need to read chunk to be safe, but spooled file has .size or we check after reading)
    # Since UploadFile is spooled, we can check size if headers provided, or read content.
    content = await resume_file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB."
        )
            
    # Save resume file
    file_extension = resume_file.filename.split(".")[-1]
    safe_email = candidate_email.replace('@', '_').replace('.', '_')
    filename = f"{safe_email}_{job_id}_{datetime.now(timezone.utc).timestamp()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename).replace("\\", "/")
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Save photo file if provided
    photo_path = None
    if photo_file:
        photo_content = await photo_file.read()
        if len(photo_content) > MAX_FILE_SIZE:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Photo too large. Maximum size is 5MB."
            )
        
        photo_ext = photo_file.filename.split(".")[-1]
        photo_filename = f"photo_{safe_email}_{job_id}_{datetime.now(timezone.utc).timestamp()}.{photo_ext}"
        photo_path = os.path.join(PHOTO_DIR, photo_filename).replace("\\", "/")
        with open(photo_path, "wb") as f:
            f.write(photo_content)
    
    # Create application
    new_application = Application(
        job_id=job_id,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        resume_file_path=file_path,
        resume_file_name=resume_file.filename,
        candidate_photo_path=photo_path,
        status="submitted"
    )
    
    try:
        db.add(new_application)
        db.commit()
        db.refresh(new_application)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save new application securely")
    
    # Parse resume with AI (async in background would be better)
    try:
        # Read resume file
        # Parse resume text based on file type
        try:
            resume_text = ""
            file_ext = file_path.lower().split('.')[-1]
            
            if file_ext == 'pdf':
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        resume_text += page.extract_text() + "\n"
                except Exception as e:
                    print(f"PDF Error: {e}")
                    # Fallback to binary decode if PDF read fails (unlikely to work but last resort)
                    with open(file_path, "rb") as f:
                        resume_text = f.read().decode('utf-8', errors='ignore')
                        
            elif file_ext in ['docx', 'doc']:
                try:
                    import docx
                    doc = docx.Document(file_path)
                    for para in doc.paragraphs:
                        resume_text += para.text + "\n"
                except Exception as e:
                    print(f"DOCX Error: {e}")
                    with open(file_path, "rb") as f:
                        resume_text = f.read().decode('utf-8', errors='ignore')
                        
            else:
                # Text file
                with open(file_path, "rb") as f:
                    resume_text = f.read().decode('utf-8', errors='ignore')
                    
            if not resume_text.strip():
                resume_text = "No readable text found in resume."
                
        except Exception as e:
            print(f"Text Extraction Error: {e}")
            resume_text = "Error extracting text."
        
        # Parse with AI
        extraction_data = await parse_resume_with_ai(
            resume_text,
            job.id,
            job.description
        )
        
        # Store extraction
        resume_extraction = ResumeExtraction(
            application_id=new_application.id,
            extracted_text=resume_text,  # Store FULL extracted text
            summary=extraction_data.get("summary", ""), # Store AI summary
            extracted_skills=json.dumps(extraction_data.get("skills") or []),
            years_of_experience=extraction_data.get("experience"),
            education=json.dumps(extraction_data.get("education") or []),
            previous_roles=json.dumps(extraction_data.get("roles") or []),
            experience_level=extraction_data.get("experience_level"),
            resume_score=extraction_data.get("score", 0),
            skill_match_percentage=extraction_data.get("match_percentage", 0)
        )
        db.add(resume_extraction)
        
        # --- Validation Logic ---
        rejection_reasons = []
        
        # 0. Check if it's a resume
        if extraction_data.get("is_resume") is False:
             rejection_reasons.append("uploaded document is not a resume")
        
        # 1. Check for parsing failure
        # Heuristic: If skills are empty or extracted text indicates failure
        if not extraction_data.get("skills") and extraction_data.get("experience") == 0:
             rejection_reasons.append("resume parsing failed")
             
        # 2. Check for experience level mismatch
        # Normalize levels for comparison
        job_level = job.experience_level.lower().strip() if job.experience_level else ""
        candidate_level = str(extraction_data.get("experience_level", "")).lower().strip()
        
        # Define hierarchy
        levels = {
            "intern": 0,
            "junior": 1,
            "mid": 2, "mid-level": 2,
            "senior": 3,
            "lead": 4, "manager": 4, "lead / manager": 4
        }
        
        job_level_rank = levels.get(job_level, -1)
        candidate_level_rank = levels.get(candidate_level, -1)
        
        # If both levels are recognized, check if candidate is lower than required
        if job_level_rank != -1 and candidate_level_rank != -1:
            if candidate_level_rank < job_level_rank:
                 rejection_reasons.append("experience level mismatch")
        
        # If rejected, update status
        raw_access_key = None
        if rejection_reasons:
            new_application.status = "rejected"
            new_application.hr_notes = f"Auto-rejected based on: {', '.join(rejection_reasons)}"
        else:
            new_application.status = "approved_for_interview"
            new_application.hr_notes = "Auto-approved for interview."
            
            import uuid
            raw_access_key = secrets.token_urlsafe(16)
            hashed_key = pwd_context.hash(raw_access_key)
            expiration = datetime.now(timezone.utc) + timedelta(hours=24)
            unique_test_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
            
            new_interview = Interview(
                test_id=unique_test_id,
                application_id=new_application.id,
                status='not_started',
                access_key_hash=hashed_key,
                expires_at=expiration,
                is_used=False
            )
            db.add(new_interview)
            
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error committing auto-rejection or approval: {e}")

        # Send notification to HR
        from app.models import Notification
        try:
            notification_type = "new_application"
            message = f"{candidate_name} has applied for the {job.title} position."
            
            if new_application.status == "rejected":
                message += f" (Auto-rejected: {', '.join(rejection_reasons)})"
                background_tasks.add_task(send_rejected_email, candidate_email, job.title, True)
            else:
                message += " (Auto-approved for interview)"
                # Generate Interview Access Key
                raw_access_key = secrets.token_urlsafe(16)
                hashed_key = pwd_context.hash(raw_access_key)
                expiration = datetime.now(timezone.utc)() + timedelta(hours=24)
                
                new_interview = Interview(
                    application_id=new_application.id,
                    status='not_started',
                    access_key_hash=hashed_key,
                    expires_at=expiration,
                    is_used=False
                )
                db.add(new_interview)
                db.commit()
                
                background_tasks.add_task(send_application_received_email, candidate_email, job.title)
                background_tasks.add_task(send_approved_for_interview_email, candidate_email, job.title, raw_access_key)
            
            notification = Notification(
                user_id=job.hr_id,
                notification_type=notification_type,
                title=f"New Application: {candidate_name}",
                message=message,
                related_application_id=new_application.id
            )
            db.add(notification)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error creating notification: {e}")

    except Exception as e:
        print(f"Error parsing resume: {e}")
        # Application is still created, just resume parsing failed
        background_tasks.add_task(send_application_received_email, candidate_email, job.title)
    
    return new_application

@router.get("", response_model=list[ApplicationDetailResponse])
def get_hr_applications(
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get all applications for HR's jobs (HR only)"""
    applications = db.query(Application).join(Job).options(
        joinedload(Application.job),
        joinedload(Application.resume_extraction),
        joinedload(Application.interview)
    ).all()
    
    return applications

@router.get("/{application_id}", response_model=ApplicationDetailResponse)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get application details (HR only)"""
    application = db.query(Application).options(
        joinedload(Application.job),
        joinedload(Application.resume_extraction),
        joinedload(Application.interview)
    ).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    
    return application

@router.put("/{application_id}/status", response_model=ApplicationDetailResponse)
def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Update application status (HR only)"""
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    
    # Validate status
    valid_statuses = ["approved_for_interview", "rejected", "review_later"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    application.status = status_update.status
    if status_update.hr_notes:
        application.hr_notes = status_update.hr_notes
    
    # Generate Interview Access Key if approved
    raw_access_key = None
    if application.status == "approved_for_interview":
        # Check if interview already exists to prevent duplicates
        existing_interview = db.query(Interview).filter(Interview.application_id == application.id).first()
        if not existing_interview:
            import uuid
            raw_access_key = secrets.token_urlsafe(16)
            hashed_key = pwd_context.hash(raw_access_key)
            expiration = datetime.now(timezone.utc) + timedelta(hours=24)
            unique_test_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
            
            new_interview = Interview(
                test_id=unique_test_id,
                application_id=application.id,
                status='not_started',
                access_key_hash=hashed_key,
                expires_at=expiration,
                is_used=False
            )
            db.add(new_interview)
    
    try:
        db.commit()
        db.refresh(application)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update application status securely")
    
    # Send email notification to candidate
    candidate_email = application.candidate_email
    job_title = application.job.title
    if application.status == "approved_for_interview" and raw_access_key:
        # Pass raw access key to email
        background_tasks.add_task(send_approved_for_interview_email, candidate_email, job_title, raw_access_key)
    elif application.status == "rejected":
        background_tasks.add_task(send_rejected_email, candidate_email, job_title, False)
        
    return application

@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an application along with associated data. HR only.
    """
    if current_user.role != "hr":
        raise HTTPException(status_code=403, detail="Only HR can delete applications")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Explicitly delete related records to avoid constraint violations
    if app.resume_extraction:
        db.delete(app.resume_extraction)
    if app.hiring_decision:
        db.delete(app.hiring_decision)
    if app.interview:
        if app.interview.report:
            db.delete(app.interview.report)
        for question in app.interview.questions:
            db.query(InterviewAnswer).filter(InterviewAnswer.question_id == question.id).delete()
            db.delete(question)
        db.delete(app.interview)

    db.delete(app)
    db.commit()
    return {"message": "Application deleted successfully"}
