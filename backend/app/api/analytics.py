from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from app.infrastructure.database import get_db
from app.domain.models import User, Job, Application, Interview, InterviewReport, InterviewQuestion, InterviewAnswer
from app.core.auth import get_current_hr
import json
import os
import traceback
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/config/skills")
async def get_skills_config():
    """Expose the canonical skill categories from the interview engine (Point 1)"""
    try:
        from interview_process.config import SKILL_CATEGORIES
        return list(SKILL_CATEGORIES.keys())
    except Exception as e:
        logger.error(f"Error loading skill categories: {e}")
        # Fallback to a basic list if import fails
        return ["backend", "frontend", "fullstack", "devops", "hr"]

@router.get("/dashboard")
async def get_dashboard_analytics(
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get enterprise analytics (100% Failure-Safe Hard Fallback)"""
    try:
        from app.services.analytics_service import AnalyticsService
        hr_id = current_user.id if current_user.role != "super_admin" else None
        
        # Call service
        metadata = AnalyticsService.get_dashboard(db, hr_id=hr_id)

        # Standard Success Format
        return {
            "success": True,
            "data": metadata,
            "error": None
        }
    except Exception as e:
        logger.error(f"[ANALYTICS][CRITICAL] {str(e)}")
        # HARD FALLBACK (NO FAILURE EVER)
        return {
            "success": True,
            "data": {
                "total_applications": 0,
                "total_interviews": 0,
                "completed_interviews": 0,
                "success_rate": 0,
                "average_score": 0
            },
            "error": None
        }



@router.get("/reports")
async def get_interview_reports(
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """
    Get all interview reports. 
    Source of truth: Interviews that are in a 'final' state (completed/terminated) 
    OR Applications that are in 'review_later'.
    """
    try:
        from sqlalchemy import or_
        # Source of truth is now the Interview/Application pair
        query = db.query(Interview)\
            .outerjoin(InterviewReport, Interview.id == InterviewReport.interview_id)\
            .outerjoin(Application, Interview.application_id == Application.id)\
            .outerjoin(Job, Application.job_id == Job.id)
        
        # Filter for "Work that should be reported"
        # We now include ALL interviews that have been completed, terminated, or are in a review/hired/rejected state.
        REPORTABLE_APPLICATION_STATUSES = [
            "interview_completed", "review_later", "hired", "rejected", 
            "offer_sent", "pending_approval", "accepted", "onboarded"
        ]
        
        query = query.filter(or_(
            Interview.status.in_(["completed", "terminated", "expired"]),
            Application.status.in_(REPORTABLE_APPLICATION_STATUSES)
        ))

        # Admin/HR globally can see reports in this version (Hardening Phase 5)
        # Filter by HR ID is disabled here to ensure cross-team visibility as requested.
        interviews = query.options(
            joinedload(Interview.application).joinedload(Application.hiring_decision),
            joinedload(Interview.report)
        ).order_by(Interview.created_at.desc()).all()

        logger.info(f"[REPORTS] Found {len(interviews)} interviews for HR {current_user.id}")
        for i in interviews:
            logger.info(f"[REPORTS] ID: {i.id}, Status: {i.status}, App Status: {i.application.status if i.application else 'N/A'}")

        reports = []
        
        # Pre-fetch all questions/answers for everything in the list
        interview_ids = [i.id for i in interviews]
        all_questions_map = {}
        all_answers_map = {}
        
        if interview_ids:
            questions = db.query(InterviewQuestion).filter(
                InterviewQuestion.interview_id.in_(interview_ids)
            ).order_by(InterviewQuestion.interview_id, InterviewQuestion.question_number).all()
            for q in questions:
                all_questions_map.setdefault(q.interview_id, []).append(q)
            
            q_ids = [q.id for q in questions]
            if q_ids:
                answers = db.query(InterviewAnswer).filter(InterviewAnswer.question_id.in_(q_ids)).all()
                for a in answers:
                    all_answers_map[a.question_id] = a

        for interview in interviews:
            report = interview.report
            app = interview.application
            job = app.job if app else None
            
            # 1. Build Profile
            candidate_profile = {
                "candidate_name": app.candidate_name if app else "Unknown",
                "candidate_email": app.candidate_email if app else "N/A",
                "applied_role": job.title if job else "N/A",
                "experience_level": "N/A",
                "primary_skill": "general",
                "skills": [],
            }
            if app and app.resume_extraction:
                candidate_profile["experience_level"] = app.resume_extraction.experience_level or "N/A"
                candidate_profile["primary_skill"] = app.resume_extraction.extracted_skills or "general"
                candidate_profile["skills"] = (app.resume_extraction.extracted_skills or "").split(",")

            # 2. Extract Q&A metrics
            question_evaluations = []
            aptitude_evals = []
            interview_questions = all_questions_map.get(interview.id, [])
            
            for q in interview_questions:
                ans = all_answers_map.get(q.id)
                evaluation = {}
                if ans and ans.answer_evaluation:
                    try:
                        evaluation = json.loads(ans.answer_evaluation) if isinstance(ans.answer_evaluation, str) else ans.answer_evaluation
                    except: pass
                
                entry = {
                    "question": q.question_text,
                    "answer": ans.answer_text if ans else "",
                    "evaluation": evaluation,
                    "score": ans.answer_score if ans else 0,
                    "question_number": q.question_number,
                    "question_type": q.question_type or "technical"
                }
                
                if q.question_type == "aptitude":
                    entry["correct"] = (ans.answer_score >= 5) if ans else False
                    aptitude_evals.append(entry)
                else:
                    question_evaluations.append(entry)

            # 3. Calculate Scores
            tech_s = [e["score"] for e in question_evaluations if e["question_type"] == "technical"]
            beh_s = [e["score"] for e in question_evaluations if e["question_type"] == "behavioral"]
            apt_qty = len(aptitude_evals)
            apt_correct = sum(1 for e in aptitude_evals if e.get("correct"))
            apt_score = (apt_correct / apt_qty * 10) if apt_qty > 0 else 0

            # 4. Construct Final Response (Unified for Real & Skeleton reports)
            created = report.created_at if report else interview.created_at
            reports.append({
                "id": report.id if report else f"skel_{interview.id}",
                "interview_id": interview.id,
                "filename": f"report_{interview.id}.json",
                "test_id": interview.test_id,
                "timestamp": created.isoformat() if created else "",
                "display_date": created.strftime("%Y-%m-%d %H:%M:%S") if created else "",
                "display_date_short": created.strftime("%b %d, %Y") if created else "",
                "status": app.status if app else interview.status,
                "overall_score": report.overall_score if report else interview.overall_score or 0,
                "final_score": report.combined_score if report else interview.overall_score or 0,
                "technical_score": sum(tech_s)/len(tech_s) if tech_s else (report.technical_skills_score if report else 0),
                "behavioral_score": sum(beh_s)/len(beh_s) if beh_s else (report.behavioral_score if report else 0),
                "aptitude_score": apt_score if apt_qty > 0 else (report.aptitude_score if report else 0),
                "total_questions_answered": len([e for e in question_evaluations if e["answer"]]),
                "aptitude_questions_answered": apt_qty,
                "question_evaluations": question_evaluations,
                "aptitude_question_evaluations": aptitude_evals,
                "candidate_profile": candidate_profile,
                "recommendation": report.recommendation if report else "consider",
                "video_url": interview.video_recording_path,
            })

        return reports
        # Final sort - newest first by timestamp (avoiding mixed type ID comparison crash)
        reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return reports

    except Exception as e:
        import traceback
        logger.critical("CRITICAL ERROR in get_interview_reports:")
        logger.error(traceback.format_exc())
        return []

@router.get("/interviews")
async def get_filtered_interviews(
    candidate_name: Optional[str] = None,
    candidate_email: Optional[str] = None,
    test_id: Optional[str] = None,
    role_applied: Optional[str] = None,
    search: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """
    Get filtered interviews for the HR user.
    """
    from sqlalchemy.orm import contains_eager, selectinload
    # FIX: Use selectinload for the report to avoid the JOIN ambiguity caused by multiple FK paths
    query = db.query(Interview)\
        .outerjoin(Interview.application)\
        .outerjoin(Application.job)\
        .options(
            contains_eager(Interview.application).contains_eager(Application.job),
            selectinload(Interview.report)
        )

    if current_user.role != "super_admin":
        from sqlalchemy import or_
        query = query.filter(or_(Application.hr_id == current_user.id, Job.hr_id == current_user.id))

    # Apply global search if present
    if search:
        from sqlalchemy import or_
        query = query.filter(or_(
            Application.candidate_name.ilike(f"%{search}%"),
            Application.candidate_email.ilike(f"%{search}%"),
            Interview.test_id.ilike(f"%{search}%"),
            Job.title.ilike(f"%{search}%")
        ))

    # Apply specific filters
    if candidate_name:
        query = query.filter(Application.candidate_name.ilike(f"%{candidate_name}%"))
    
    if candidate_email:
        query = query.filter(Application.candidate_email.ilike(f"%{candidate_email}%"))
    
    if test_id:
        query = query.filter(Interview.test_id.ilike(f"%{test_id}%"))
    
    if role_applied:
        query = query.filter(Job.title.ilike(f"%{role_applied}%"))
    
    if status and status != "all":
        query = query.filter(Interview.status == status)
    
    if date:
        try:
            # Expecting YYYY-MM-DD
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            from sqlalchemy import cast, Date
            query = query.filter(cast(Interview.created_at, Date) == filter_date)
        except ValueError:
            pass # Ignore invalid date format

    # Order by newest first
    interviews = query.order_by(Interview.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for interview in interviews:
        application = interview.application
        job = application.job if application else None
        
        result.append({
            "id": interview.id,
            "test_id": interview.test_id,
            "candidate_name": application.candidate_name if application else "Unknown",
            "candidate_email": application.candidate_email if application else "Unknown",
            "job_title": job.title if job else "Unknown",
            "date": interview.created_at.isoformat() if interview.created_at else None,
            "status": interview.status,
            "report_id": interview.report.id if interview.report else None
        })

    return result

