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

@router.get("/ranking/{job_id}")
def get_candidate_ranking(
    job_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get ranked candidates for a specific job (Point 3)"""
    from app.services.candidate_service import CandidateService
    service = CandidateService(db)
    ranked = service.get_ranked_candidates(job_id)
    
    result = []
    for idx, app in enumerate(ranked):
        result.append({
            "rank": idx + 1,
            "id": app.id,
            "candidate_name": app.candidate_name,
            "composite_score": app.composite_score,
            "recommendation": app.recommendation,
            "status": app.status
        })
    return result


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
    
    # Absolute path for saving the file
    abs_file_path = os.path.join(UPLOAD_DIR, filename).replace("\\", "/")
    # Relative path for storing in DB (starts with 'uploads/')
    rel_file_path = f"uploads/resumes/{filename}"
    
    with open(abs_file_path, "wb") as f:
        f.write(content)
    
    # Save photo file if provided
    rel_photo_path = None
    if photo_file:
        photo_content = await photo_file.read()
        if len(photo_content) > MAX_FILE_SIZE:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Photo too large. Maximum size is 5MB."
            )
        
        photo_ext = photo_file.filename.split(".")[-1]
        photo_filename = f"photo_{safe_email}_{job_id}_{datetime.now(timezone.utc).timestamp()}.{photo_ext}"
        
        # Absolute path for saving
        abs_photo_path = os.path.join(PHOTO_DIR, photo_filename).replace("\\", "/")
        # Relative path for DB
        rel_photo_path = f"uploads/photos/{photo_filename}"
        
        with open(abs_photo_path, "wb") as f:
            f.write(photo_content)
    
    # Create application
    new_application = Application(
        job_id=job_id,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        resume_file_path=rel_file_path,
        resume_file_name=resume_file.filename,
        candidate_photo_path=rel_photo_path,
        status="submitted"
    )
    
    try:
        db.add(new_application)
        db.commit()
        db.refresh(new_application)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save new application securely")
    
    # Move all heavy processing to background task to prevent timeouts (Point 10 - Robustness)
    background_tasks.add_task(
        process_application_background, 
        new_application.id, 
        job_id, 
        abs_file_path, 
        candidate_email, 
        candidate_name
    )
    
    return new_application

async def process_application_background(application_id: int, job_id: int, abs_file_path: str, candidate_email: str, candidate_name: str):
    """Heavy AI processing and notification workflow in background"""
    db = SessionLocal()
    try:
        from app.services.candidate_service import CandidateService
        cand_service = CandidateService(db)
        
        # Reload objects in this session
        application = db.query(Application).filter(Application.id == application_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()
        if not application or not job:
            db.close()
            return

        # 1. Initial State
        cand_service.advance_stage(application_id, "Application Submitted", "pass")
        cand_service.create_audit_log(None, "APPLICATION_SUBMITTED", "Application", application_id, {"email": candidate_email})
        
        # 2. Screening Stage
        cand_service.advance_stage(application_id, "Resume Screening", "pending")
        
        # Parse resume text based on file type
        resume_text = ""
        try:
            file_ext = abs_file_path.lower().split('.')[-1]
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
            print(f"Background Text Extraction Error: {e}")
            cand_service.create_audit_log(None, "RESUME_TEXT_EXTRACTION_FAILED", "Application", application_id, {"error": str(e)})
            resume_text = "Error extracting text."
        
        if not resume_text.strip():
            resume_text = "No readable text found."

        # AI Parsing
        extraction_data = await parse_resume_with_ai(resume_text, job_id, job.description)
        
        # Store extraction
        resume_extraction = ResumeExtraction(
            application_id=application_id,
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
        db.add(resume_extraction)
        
        # Update Application summary fields
        application.resume_score = extraction_data.get("score", 0)
        db.commit()

        # Recommendation and Progression
        res_score_norm = extraction_data.get("score", 0) * 10
        match_perc = extraction_data.get("match_percentage", 0)
        avg_score = (res_score_norm + match_perc) / 2
        
        status = "pass" if avg_score >= 70 else ("fail" if avg_score < 40 else "hold")
        note = "Strong match - automated progression" if status == "pass" else ("Low compatibility" if status == "fail" else "Manual review required")
        
        cand_service.advance_stage(application_id, "Resume Screening", status, avg_score, note)
        cand_service.create_audit_log(None, "RESUME_SCREENING_COMPLETED", "Application", application_id, {"avg_score": avg_score, "status": status})

        # Notifications
        if status == "pass":
            # Direct pass to aptitude
            raw_access_key = secrets.token_urlsafe(16)
            hashed_key = pwd_context.hash(raw_access_key) # Use pwd_context.hash
            expiration = datetime.now(timezone.utc) + timedelta(hours=24)
            
            new_interview = Interview(
                test_id=f"TEST-{secrets.token_hex(4).upper()}",
                application_id=application_id,
                status='not_started',
                access_key_hash=hashed_key,
                expires_at=expiration,
                is_used=False # Added missing field
            )
            db.add(new_interview)
            application.status = "approved_for_interview" # Update application status
            await send_approved_for_interview_email(candidate_email, job.title, raw_access_key)
        elif status == "fail":
            application.status = "rejected" # Update application status
            await send_rejected_email(candidate_email, job.title, True) # Auto-rejected
        else: # hold
            application.status = "submitted" # Keep as submitted for manual review
            await send_application_received_email(candidate_email, job.title)
            
        db.commit()
    except Exception as e:
        print(f"CRITICAL Background Error processing application {application_id}: {e}")
        db.rollback()
        # Log the critical error
        try:
            cand_service = CandidateService(db) # Re-initialize if needed, or pass db
            cand_service.create_audit_log(None, "BACKGROUND_PROCESSING_FAILED", "Application", application_id, {"error": str(e)})
            # Optionally update application status to indicate processing failed
            application = db.query(Application).filter(Application.id == application_id).first()
            if application:
                application.status = "processing_failed"
                application.hr_notes = f"Automated processing failed: {e}"
                db.commit()
        except Exception as log_e:
            print(f"Failed to log critical error for application {application_id}: {log_e}")
    finally:
        db.close()
    
    # The return value of a background task is not used by FastAPI.
    # The original snippet returned new_application, but it's not necessary here.
    # Keeping it for consistency with the provided snippet, but it has no effect.
    return application 

@router.get("", response_model=list[ApplicationDetailResponse])
def get_hr_applications(
    job_id: int = None,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get all applications for HR's jobs (HR only)"""
    # Join with stages for visualization (Point 12)
    # Use outerjoin to ensure apps with missing jobs (shouldn't happen but safe) still show or at least don't crash
    query = db.query(Application).outerjoin(Job).options(
        joinedload(Application.job),
        joinedload(Application.resume_extraction),
        joinedload(Application.interview),
        joinedload(Application.pipeline_stages)
    )
    
    # Filter by job if requested
    if job_id:
        query = query.filter(Application.job_id == job_id)
        
    # Security: Only admins can see everything. Others see their own jobs' apps.
    if current_user.role != "admin":
        print(f"DEBUG: Filtering applications for HR ID {current_user.id}")
        query = query.filter(Job.hr_id == current_user.id)
    else:
        print("DEBUG: Admin viewing all applications")
        
    applications = query.all()
    print(f"DEBUG: Found {len(applications)} applications for user {current_user.id}")
    
    for app in applications:
        if app.candidate_photo_path and ":" in app.candidate_photo_path:
            idx = app.candidate_photo_path.find("uploads")
            if idx != -1:
                app.candidate_photo_path = app.candidate_photo_path[idx:].replace("\\", "/")
        if app.resume_file_path and ":" in app.resume_file_path:
            idx = app.resume_file_path.find("uploads")
            if idx != -1:
                app.resume_file_path = app.resume_file_path[idx:].replace("\\", "/")
    
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
        joinedload(Application.interview),
        joinedload(Application.pipeline_stages)
    ).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Sanitize paths
    if application.candidate_photo_path and ":" in application.candidate_photo_path:
        idx = application.candidate_photo_path.find("uploads")
        if idx != -1:
            application.candidate_photo_path = application.candidate_photo_path[idx:].replace("\\", "/")
    if application.resume_file_path and ":" in application.resume_file_path:
        idx = application.resume_file_path.find("uploads")
        if idx != -1:
            application.resume_file_path = application.resume_file_path[idx:].replace("\\", "/")
    
    return application

@router.put("/{application_id}/status", response_model=ApplicationDetailResponse)
def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Update application status & Advance Pipeline (Point 1)"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    from app.services.candidate_service import CandidateService
    cand_service = CandidateService(db)

    # Valid statuses for the simplified HR view (will mapping to pipeline stages)
    valid_statuses = ["approved_for_interview", "rejected", "review_later", "technical_interview", "hr_interview", "hired"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status.")
    
    old_status = application.status
    application.status = status_update.status
    if status_update.hr_notes:
        application.hr_notes = status_update.hr_notes
    
    # Advance Pipeline Stages (Point 1)
    if status_update.status == "approved_for_interview":
        cand_service.advance_stage(application.id, "Resume Screening", "pass", notes=status_update.hr_notes, evaluator_id=current_user.id)
        cand_service.advance_stage(application.id, "Aptitude Round", "pending")
    elif status_update.status == "technical_interview":
        cand_service.advance_stage(application.id, "Technical Interview", "pending", evaluator_id=current_user.id)
    elif status_update.status == "hr_interview":
        cand_service.advance_stage(application.id, "HR Interview", "pending", evaluator_id=current_user.id)
    elif status_update.status == "hired":
        cand_service.advance_stage(application.id, "Final Decision", "pass", notes=status_update.hr_notes, evaluator_id=current_user.id)
    elif status_update.status == "rejected":
        # Record failure in current stage
        current_stage = "Resume Screening" if old_status == "submitted" else "Final Decision"
        cand_service.advance_stage(application.id, current_stage, "fail", notes=status_update.hr_notes, evaluator_id=current_user.id)

    # Logging
    cand_service.create_audit_log(current_user.id, "STATUS_UPDATED", "Application", application.id, {"from": old_status, "to": status_update.status})

    # Generate Interview Access Key if approved
    raw_access_key = None
    if application.status == "approved_for_interview":
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
    
    db.commit()
    db.refresh(application)
    
    # Notifications (Point 9)
    candidate_email = application.candidate_email
    job_title = application.job.title
    if application.status == "approved_for_interview" and raw_access_key:
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
