from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import secrets

from app.infrastructure.database import get_db
from app.domain.models import InterviewIssue, InterviewFeedback, Interview, Application, User
from app.domain.schemas import (
    InterviewIssueCreate, InterviewIssueResponse, InterviewIssueResolve,
    InterviewFeedbackCreate, InterviewFeedbackResponse, GeneralGrievanceCreate
)
from app.core.auth import get_current_user, hash_password, verify_password, get_current_hr
from app.services.email_service import send_ticket_resolved_email, send_key_reissued_email

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])

@router.post("", response_model=InterviewIssueResponse)
def report_issue(issue: InterviewIssueCreate, db: Session = Depends(get_db)):
    # Verify interview exists
    interview = db.query(Interview).filter(Interview.id == issue.interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    application = interview.application
    
    new_issue = InterviewIssue(
        interview_id=issue.interview_id,
        candidate_name=application.candidate_name,
        candidate_email=application.candidate_email,
        issue_type=issue.issue_type,
        description=issue.description,
        status='pending'
    )
    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)
    
    # Add extra fields for response
    new_issue.application_id = application.id
    new_issue.test_id = interview.test_id
    new_issue.job_id = application.job_id
    new_issue.job_identifier = application.job.job_id
    return new_issue

@router.post("/grievance", response_model=InterviewIssueResponse)
def report_grievance(issue: GeneralGrievanceCreate, db: Session = Depends(get_db)):
    # Find the most recent interview for this email
    interview = db.query(Interview).join(Application).filter(
        Application.candidate_email == issue.email.lower().strip()
    ).order_by(Interview.created_at.desc()).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="No interview found for this email. Please ensure you've been invited.")

    # Verify access key
    if not verify_password(issue.access_key, interview.access_key_hash):
        raise HTTPException(status_code=401, detail="Invalid access key. Use the key from your invitation email.")

    new_issue = InterviewIssue(
        interview_id=interview.id,
        candidate_name=interview.application.candidate_name,
        candidate_email=issue.email,
        issue_type=issue.issue_type,
        description=issue.description,
        status='pending'
    )
    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)
    
    # Add extra fields for response
    new_issue.application_id = interview.application_id
    new_issue.test_id = interview.test_id
    new_issue.job_id = interview.application.job_id
    new_issue.job_identifier = interview.application.job.job_id
    return new_issue

@router.post("/feedback", response_model=InterviewFeedbackResponse)
def submit_feedback(feedback: InterviewFeedbackCreate, db: Session = Depends(get_db)):
    # Verify interview exists
    interview = db.query(Interview).filter(Interview.id == feedback.interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Check if feedback already exists
    existing = db.query(InterviewFeedback).filter(InterviewFeedback.interview_id == feedback.interview_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Feedback already submitted for this interview")

    new_feedback = InterviewFeedback(
        interview_id=feedback.interview_id,
        ui_ux_rating=feedback.ui_ux_rating,
        feedback_text=feedback.feedback_text
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)
    return new_feedback

@router.get("/count")
def get_ticket_count(
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Lightweight endpoint returning just the pending ticket count for sidebar badges."""
    count = db.query(InterviewIssue).filter(InterviewIssue.status == 'pending').count()
    return {"count": count}

@router.get("", response_model=List[InterviewIssueResponse])
def get_tickets(
    status: str = 'pending',
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    query = db.query(InterviewIssue)
    if status != 'all':
        query = query.filter(InterviewIssue.status == status)
    
    tickets = query.order_by(InterviewIssue.created_at.desc()).all()
    
    # Hybrid population
    for t in tickets:
        if t.interview:
            t.application_id = t.interview.application_id
            t.test_id = t.interview.test_id
            if t.interview.application:
                t.job_id = t.interview.application.job_id
                if t.interview.application.job:
                    t.job_identifier = t.interview.application.job.job_id
                else:
                    t.job_identifier = None
            else:
                t.job_id = None
                t.job_identifier = None
        else:
            t.application_id = None
            t.test_id = None
            t.job_id = None
            t.job_identifier = None
        
    return tickets

@router.put("/{ticket_id}/resolve", response_model=InterviewIssueResponse)
async def resolve_ticket(
    ticket_id: int,
    resolution: InterviewIssueResolve,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    ticket = db.query(InterviewIssue).filter(InterviewIssue.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Status update logic
    if resolution.action == 'reissue_key':
        ticket.status = 'resolved'
    elif resolution.action in ['resolved', 'dismissed']:
        ticket.status = resolution.action
    elif resolution.action == 'reply':
        # Just update response and send email, keep status as pending
        ticket.status = 'pending'
    
    ticket.hr_response = resolution.hr_response
    ticket.resolved_at = datetime.now() if ticket.status != 'pending' else None
    
    interview = ticket.interview
    if not interview:
        # If interview is missing, we can only update the ticket status, not send emails or reissue
        db.commit()
        db.refresh(ticket)
        ticket.application_id = None
        ticket.test_id = None
        ticket.job_id = None
        ticket.job_identifier = None
        return ticket

    application = interview.application
    
    if resolution.action == 'reissue_key':
        # Generate new access key
        new_key = secrets.token_urlsafe(16)
        ticket.interview.access_key_hash = hash_password(new_key)
        ticket.interview.is_used = False
        ticket.interview.status = 'not_started'
        ticket.is_reissue_granted = True
        
        # Send reissue email if requested
        if resolution.send_email:
            await send_key_reissued_email(
                to_email=ticket.candidate_email,
                job_title=application.job.title,
                new_key=new_key,
                hr_response=resolution.hr_response
            )
            print(f"RE-ISSUED KEY for {ticket.candidate_email}: {new_key}")
    else:
        # Send resolution/dismissal email if requested
        if resolution.send_email:
            await send_ticket_resolved_email(
                to_email=ticket.candidate_email,
                issue_type=ticket.issue_type,
                hr_response=resolution.hr_response,
                job_title=application.job.title
            )

    db.commit()
    db.refresh(ticket)
    
    # Populate extra fields for response
    ticket.application_id = application.id
    ticket.test_id = interview.test_id
    ticket.job_id = application.job_id
    ticket.job_identifier = application.job.job_id
    
    return ticket
