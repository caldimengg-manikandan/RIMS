from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.models import User, Job, Application, Interview, InterviewReport, InterviewQuestion, InterviewAnswer
from app.auth import get_current_user
import json
from datetime import datetime

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated analytics for the HR dashboard.
    Only accessible by HR users.
    """
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied"
        )

    # 1. Key Statistics
    # Filter everything by the HR user's jobs
    hr_job_ids = [j.id for j in db.query(Job.id).all()]
    
    open_jobs_count = db.query(Job).filter(Job.status == "open").count()
    
    total_applications = db.query(Application).join(Job).count()
    pending_review = db.query(Application).join(Job).filter(Application.status == "submitted").count()
    
    active_interviews = db.query(Interview).join(Application).join(Job).filter(
        Interview.status.in_(["scheduled", "in_progress"])
    ).count()
    
    offers_made = db.query(Application).join(Job).filter(Application.status == "hired").count()

    # 2. Application Status Distribution (for Charts)
    # Group by status and count within HR's domain
    status_counts = db.query(
        Application.status, func.count(Application.id)
    ).join(Job).group_by(Application.status).all()
    
    # Format for frontend chart [{name: "Hired", value: 10}, ...]
    chart_data = []
    for app_status, count in status_counts:
        status_label = "Unknown"
        if app_status:
            status_label = app_status.replace("_", " ").title()
        
        chart_data.append({"name": status_label, "value": count})

    # 3. Recent Interviews (Upcoming & Recent Past)
    # Single query with eager loading — eliminates N+1
    recent_interviews_query = db.query(Interview).join(Application).join(Job).options(
        joinedload(Interview.application).joinedload(Application.job)
    ).order_by(
        Interview.created_at.desc()
    ).limit(5).all()

    recent_interviews_data = []
    for interview in recent_interviews_query:
        application = interview.application
        job = application.job if application else None

        recent_interviews_data.append({
            "id": interview.id,
            "test_id": interview.test_id,
            "candidate_name": application.candidate_name if application else "Unknown",
            "job_title": job.title if job else "Unknown",
            "date": interview.created_at.isoformat() if interview.created_at else None,
            "status": interview.status
        })

    return {
        "stats": {
            "open_jobs": open_jobs_count,
            "total_applications": total_applications,
            "pending_review": pending_review,
            "active_interviews": active_interviews,
            "offers_made": offers_made
        },
        "chart_data": chart_data,
        "recent_interviews": recent_interviews_data
    }



@router.get("/reports")
async def get_interview_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all interview reports from DB and merge/sync with local JSON files."""
    if current_user.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied"
        )

    # 1. Query all reports from DB and filter by HR ID
    db_reports = db.query(InterviewReport).join(Interview).join(Application).join(Job).filter(
        Job.hr_id == current_user.id
    ).options(
        joinedload(InterviewReport.interview)
        .joinedload(Interview.application)
        .joinedload(Application.hiring_decision)
    ).order_by(InterviewReport.created_at.desc()).all()

    reports = []
    seen_test_ids = set()

    def process_raw_report(report, interview=None, application=None):
        # Build candidate profile
        candidate_profile = {}
        experience_level = "N/A"
        primary_skill = "general"
        
        if application:
            candidate_profile = {
                "candidate_name": report.candidate_name or application.candidate_name,
                "candidate_email": report.candidate_email or application.candidate_email,
                "applied_role": report.applied_role or "",
            }
            if application.resume_extraction:
                experience_level = application.resume_extraction.experience_level or "N/A"
                primary_skill = application.resume_extraction.extracted_skills or "general"
            candidate_profile["experience_level"] = experience_level
            candidate_profile["primary_skill"] = primary_skill
            candidate_profile["skills"] = primary_skill.split(",") if primary_skill else []
        else:
            candidate_profile = {
                "candidate_name": report.candidate_name or "Unknown",
                "candidate_email": report.candidate_email or "",
                "applied_role": report.applied_role or "",
                "experience_level": "N/A",
                "primary_skill": "general",
                "skills": [],
            }

        # Question evals
        question_evaluations = []
        aptitude_question_evaluations = []
        technical_scores = []
        behavioral_scores = []
        
        if interview:
            all_questions = db.query(InterviewQuestion).filter(
                InterviewQuestion.interview_id == interview.id
            ).order_by(InterviewQuestion.question_number).all()

            q_ids = [q.id for q in all_questions]
            answers_map = {}
            if q_ids:
                answers = db.query(InterviewAnswer).filter(
                    InterviewAnswer.question_id.in_(q_ids)
                ).all()
                answers_map = {a.question_id: a for a in answers}

            for q in all_questions:
                ans = answers_map.get(q.id)
                evaluation = {}
                if ans:
                    if ans.answer_evaluation:
                        try:
                            evaluation = json.loads(ans.answer_evaluation) if isinstance(ans.answer_evaluation, str) else ans.answer_evaluation
                        except Exception:
                            evaluation = {}
                    evaluation.setdefault("overall", ans.answer_score or 0)

                q_type = (q.question_type or "technical").lower()
                entry = {
                    "question": q.question_text,
                    "answer": ans.answer_text if ans else "",
                    "evaluation": evaluation,
                    "score": ans.answer_score if ans else 0,
                    "question_number": q.question_number,
                    "question_type": q_type
                }

                if q_type == "aptitude":
                    entry["correct"] = (ans.answer_score >= 5) if ans else False
                    aptitude_question_evaluations.append(entry)
                else:
                    if q_type == "behavioral":
                        behavioral_scores.append(ans.answer_score or 0 if ans else 0)
                    else:
                        technical_scores.append(ans.answer_score or 0 if ans else 0)
                    question_evaluations.append(entry)

        # Fallback to detailed_feedback if no questions found
        if not question_evaluations and not aptitude_question_evaluations and hasattr(report, 'detailed_feedback') and report.detailed_feedback:
            try:
                feedback_data = json.loads(report.detailed_feedback) if isinstance(report.detailed_feedback, str) else report.detailed_feedback
                feedback_list = []
                if isinstance(feedback_data, dict):
                    feedback_list = feedback_data.get("question_evaluations", [])
                elif isinstance(feedback_data, list):
                    feedback_list = feedback_data
                
                for idx, q_data in enumerate(feedback_list):
                    q_type = q_data.get("question_type", "technical").lower()
                    entry = {
                        "question": q_data.get("question", ""),
                        "answer": q_data.get("answer", ""),
                        "evaluation": q_data.get("evaluation", {}),
                        "score": q_data.get("score", q_data.get("evaluation", {}).get("overall", 0)),
                        "question_number": q_data.get("question_number", idx + 1),
                        "question_type": q_type
                    }
                    if q_type == "aptitude":
                        aptitude_question_evaluations.append(entry)
                    else:
                        question_evaluations.append(entry)
            except:
                pass

        # Overall formatting
        created = report.created_at
        return {
            "id": report.id,
            "filename": f"report_{report.id}.json",
            "test_id": interview.test_id if interview else None,
            "timestamp": created.isoformat() if created else "",
            "display_date": created.strftime("%Y-%m-%d %H:%M:%S") if created else "",
            "display_date_short": created.strftime("%b %d, %Y") if created else "",
            "status": interview.status if interview else "completed",
            "overall_score": report.overall_score or 0,
            "final_score": report.combined_score or report.overall_score or 0,
            "total_questions_answered": len(question_evaluations),
            "aptitude_questions_answered": len(aptitude_question_evaluations),
            "question_evaluations": question_evaluations,
            "aptitude_question_evaluations": aptitude_question_evaluations,
            "candidate_profile": candidate_profile,
            "tech_score": report.technical_skills_score,
            "comm_score": report.communication_score,
            "evaluated_skills": report.evaluated_skills,
        }

    # Process DB reports
    for report in db_reports:
        processed = process_raw_report(report, report.interview, report.interview.application if report.interview else None)
        if processed["test_id"]:
            seen_test_ids.add(processed["test_id"])
        reports.append(processed)

    # Process Local File reports
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reports_dir = os.path.join(backend_dir, "interview_reports")
    
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(reports_dir, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        t_id = data.get("test_id")
                        if t_id and t_id not in seen_test_ids:
                            # Minimal mapping for file-based reports to satisfy frontend
                            cand = data.get("candidate_profile", {})
                            reports.append({
                                "id": f"file_{filename}",
                                "filename": filename,
                                "test_id": t_id,
                                "timestamp": data.get("timestamp", data.get("created_at", "")),
                                "display_date": data.get("display_date", ""),
                                "display_date_short": data.get("display_date_short", ""),
                                "status": data.get("status", "completed"),
                                "overall_score": data.get("overall_score") or data.get("final_score") or 0,
                                "final_score": data.get("final_score") or 0,
                                "total_questions_answered": len(data.get("question_evaluations", [])),
                                "question_evaluations": data.get("question_evaluations", []),
                                "aptitude_question_evaluations": data.get("aptitude_question_evaluations", []),
                                "candidate_profile": cand,
                                "tech_score": data.get("tech_score"),
                                "comm_score": data.get("comm_score"),
                                "evaluated_skills": data.get("evaluated_skills"),
                                "source": "file"
                            })
                            seen_test_ids.add(t_id)
                except Exception as e:
                    print(f"Error reading report file {filename}: {e}")

    # Final sort - newest first
    reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return reports



@router.get("/interviews")
async def get_filtered_interviews(
    candidate_name: Optional[str] = None,
    candidate_email: Optional[str] = None,
    test_id: Optional[str] = None,
    role_applied: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get filtered interviews for the HR user.
    """
    if current_user.role != "hr":
        raise HTTPException(
            status_code=403, 
            detail="Access denied"
        )

    query = db.query(Interview).join(Application).join(Job)

    # Apply filters
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
            query = query.filter(func.date(Interview.created_at) == filter_date)
        except ValueError:
            pass # Ignore invalid date format

    # Order by newest first
    interviews = query.order_by(Interview.created_at.desc()).all()

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
            "status": interview.status
        })

    return result


