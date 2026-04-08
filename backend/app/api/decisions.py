from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Form, File, UploadFile
import os
import shutil
from sqlalchemy import or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.infrastructure.database import get_db
from app.domain.models import User, Application, HiringDecision, Notification, Job, Interview
from app.domain.schemas import HiringDecisionMake, HiringDecisionResponse
from app.core.auth import get_current_user, get_current_hr
from app.core.ownership import validate_hr_ownership
from app.services.email_service import send_hired_email, send_rejected_email

router = APIRouter(prefix="/api/decisions", tags=["hiring decisions"])

@router.put("/applications/{application_id}/decide", response_model=HiringDecisionResponse)
def make_hiring_decision(
    application_id: int,
    decision_data: HiringDecisionMake,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Make hiring decision (HR only) — uses FSM for state transitions."""
    from app.services.state_machine import (
        CandidateStateMachine, TransitionAction,
        InvalidTransitionError, DuplicateTransitionError,
    )
    
    """Make hiring decision (HR only)"""
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    validate_hr_ownership(application, current_user, resource_name="application")
    
    # Use FSM for state transition (Guards are centralized in CandidateStateMachine)
    fsm = CandidateStateMachine(db)
    action = TransitionAction.HIRE if decision_data.decision == "hired" else TransitionAction.REJECT
    
    try:
        result = fsm.transition(
            application=application,
            action=action,
            user_id=current_user.id,
            notes=decision_data.decision_comments,
        )
    except (InvalidTransitionError, DuplicateTransitionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create decision record
    hiring_decision = HiringDecision(
        application_id=application_id,
        hr_id=current_user.id,
        decision=decision_data.decision,
        decision_comments=decision_data.decision_comments,
        decided_at=datetime.now(timezone.utc)
    )
    
    
    try:
        db.add(hiring_decision)
        db.commit()
        db.refresh(hiring_decision)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save hiring decision securely")
    
    # Email notifications — ONLY after successful commit
    candidate_email = application.candidate_email
    job = application.job
    
    if result.email_type == "hired":
        background_tasks.add_task(send_hired_email, candidate_email, job.title, application.interview)
    elif result.email_type == "rejected":
        background_tasks.add_task(send_rejected_email, candidate_email, job.title, False)
    elif result.email_type == "approved_for_interview":
        # Note: raw_access_key would be needed here if this action was APPROVE_FOR_INTERVIEW
        # But this endpoint is for HIRE/REJECT. FSM might return approved_for_interview if state was weird.
        pass
    
    return hiring_decision

@router.post("/applications/{application_id}/hire")
async def hire_candidate(
    application_id: int,
    joining_date: str = Form(...),
    notes: str = Form(None),
    offer_letter: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Final Hire Action with Offer Letter Generation & Email (Multipart/Form-Data)"""
    from app.services.state_machine import (
        CandidateStateMachine, TransitionAction,
        InvalidTransitionError, DuplicateTransitionError,
    )
    from app.services.pdf_service import overlay_offer_letter_details
    from app.core.config import get_settings
    settings = get_settings()

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    validate_hr_ownership(application, current_user, resource_name="application")

    # 1. State machine transition
    fsm = CandidateStateMachine(db)
    try:
        result = fsm.transition(
            application=application,
            action=TransitionAction.HIRE,
            user_id=current_user.id,
            notes=notes or "Hired via formal process",
        )
    except (InvalidTransitionError, DuplicateTransitionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Save the uploaded offer letter
    # 2. Upload the base offer letter to Supabase
    timestamp = int(datetime.now(timezone.utc).timestamp())
    base_filename = f"offer_base_{application_id}_{timestamp}.pdf"
    base_storage_path = f"offer_letters/{base_filename}"
    
    content = await offer_letter.read()
    from app.core.storage import upload_file
    upload_file(settings.supabase_bucket_resumes, base_storage_path, content, content_type=offer_letter.content_type)

    # 3. Process the PDF (Overlay details in-memory)
    try:
        jdate = datetime.fromisoformat(joining_date.replace('Z', '+00:00'))
    except:
        jdate = datetime.now(timezone.utc)

    final_pdf_content = overlay_offer_letter_details(
        content, 
        application.candidate_name, 
        application.job.title, 
        jdate
    )
    
    final_filename = f"offer_final_{application_id}_{timestamp}.pdf"
    final_storage_path = f"offer_letters/{final_filename}"
    upload_file(settings.supabase_bucket_resumes, final_storage_path, final_pdf_content, content_type="application/pdf")

    # 4. Create decision record
    hiring_decision = HiringDecision(
        application_id=application_id,
        hr_id=current_user.id,
        decision="hired",
        decision_comments=notes,
        joining_date=jdate,
        offer_letter_path=final_storage_path,
        decided_at=datetime.now(timezone.utc)
    )
    db.add(hiring_decision)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save hiring decision")

    # 5. Email with attachment (ONLY after successful commit)
    candidate_email = application.candidate_email
    job_title = application.job.title

    if result.email_type == "hired":
        background_tasks.add_task(
            send_hired_email, 
            candidate_email, 
            job_title, 
            application.interview,
            offer_letter_path=final_storage_path
        )

    return {"status": "success", "message": "Candidate hired and offer letter sent"}

@router.get("/applications/{application_id}/decision")
def get_application_decision(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get hiring decision for application"""
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    if current_user.role != "super_admin":
        # Allow only owner HR or candidate tied to this application email.
        if current_user.role == "hr":
            validate_hr_ownership(application, current_user, resource_name="application")
        elif current_user.role == "candidate":
            if (application.candidate_email or "").lower() != (current_user.email or "").lower():
                raise HTTPException(status_code=403, detail="Unauthorized access")
    
    
    decision = db.query(HiringDecision).filter(
        HiringDecision.application_id == application_id
    ).first()
    
    if not decision:
        return {"message": "Decision not yet made"}
    
    return decision

@router.get("/pipeline")
def get_hiring_pipeline(
    status_filter: str = None,
    job_id: int = None,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get hiring pipeline for all applications (HR only)"""
    from sqlalchemy.orm import joinedload, load_only
    
    query = db.query(Application).outerjoin(Job).options(
        joinedload(Application.job).load_only(Job.id, Job.title, Job.hr_id),
        joinedload(Application.interview).load_only(Interview.id, Interview.status, Interview.overall_score),
        joinedload(Application.hiring_decision).load_only(HiringDecision.decision, HiringDecision.decided_at),
        load_only(Application.id, Application.candidate_name, Application.status, Application.applied_at, Application.job_id, Application.hr_id)
    )
    
    if job_id:
        query = query.filter(Application.job_id == job_id)
    
    if status_filter:
        query = query.filter(Application.status == status_filter)

    if current_user.role != "super_admin":
        query = query.filter(or_(Application.hr_id == current_user.id, Job.hr_id == current_user.id))
    
    applications = query.all()
    
    # Build detailed response — all data already loaded, zero extra queries
    pipeline = []
    for app in applications:
        app_data = {
            "application_id": app.id,
            "candidate_name": app.candidate_name,
            "job_title": app.job.title,
            "status": app.status,
            "applied_at": app.applied_at,
            "interview": None,
            "decision": None
        }
        
        if app.interview:
            app_data["interview"] = {
                "id": app.interview.id,
                "status": app.interview.status,
                "score": app.interview.overall_score
            }
        
        if app.hiring_decision:
            app_data["decision"] = {
                "decision": app.hiring_decision.decision,
                "decided_at": app.hiring_decision.decided_at
            }
        
        pipeline.append(app_data)
    
    return pipeline
