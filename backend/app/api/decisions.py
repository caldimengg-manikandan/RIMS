from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.infrastructure.database import get_db
from app.domain.models import User, Application, HiringDecision, Notification, Job
from app.domain.schemas import HiringDecisionMake, HiringDecisionResponse
from app.core.auth import get_current_user, get_current_hr
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
    
    
    # Strict Workflow: Check if interview is completed
    # For HR approval, we require first_level_completed
    if not application.interview or not application.interview.first_level_completed:
        # Override manual allowance for candidates who didn't even start, 
        # but only if HR is rejecting them outright.
        if decision_data.decision == "rejected" and application.status == "approved_for_interview":
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot make hiring decision: Interview's first level is not completed."
            )
    
    # Validate decision
    if decision_data.decision not in ["hired", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'hired' or 'rejected'"
        )
    
    # Check if decision already exists
    existing_decision = db.query(HiringDecision).filter(
        HiringDecision.application_id == application_id
    ).first()
    
    if existing_decision:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision already made for this application"
        )
    
    # Use FSM for state transition
    fsm = CandidateStateMachine(db)
    action = TransitionAction.HIRE if decision_data.decision == "hired" else TransitionAction.REJECT
    
    try:
        result = fsm.transition(
            application=application,
            action=action,
            user_id=current_user.id,
            notes=decision_data.decision_comments,
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DuplicateTransitionError as e:
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
    
    return hiring_decision

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
    from sqlalchemy.orm import joinedload, selectinload
    
    query = db.query(Application).join(Job).options(
        joinedload(Application.job),
        joinedload(Application.interview),
        joinedload(Application.hiring_decision),
    )
    
    if job_id:
        query = query.filter(Application.job_id == job_id)
    
    if status_filter:
        query = query.filter(Application.status == status_filter)
    
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
