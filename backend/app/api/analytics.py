from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from app.infrastructure.database import get_db
from app.domain.models import User, Job, Application, Interview, InterviewReport, InterviewQuestion, InterviewAnswer
from app.core.auth import get_current_user
import json
import os
import traceback
from datetime import datetime

router = APIRouter()

@router.get("/config/skills")
async def get_skills_config():
    """Expose the canonical skill categories from the interview engine (Point 1)"""
    try:
        from interview_process.config import SKILL_CATEGORIES
        return list(SKILL_CATEGORIES.keys())
    except Exception as e:
        print(f"Error loading skill categories: {e}")
        # Fallback to a basic list if import fails
        return ["backend", "frontend", "fullstack", "devops", "hr"]

@router.get("/dashboard")
async def get_dashboard_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enterprise analytics (Point 5)"""
    try:
        from app.services.analytics_service import AnalyticsService
        service = AnalyticsService(db)
        
        # Permission check (enterprise roles including legacy 'hr')
        if current_user.role not in ["admin", "hr_manager", "recruiter", "hr"]:
            raise HTTPException(status_code=403, detail="Access denied")

        print(f"DEBUG: Dashboard analytics requested by user {current_user.id} (role={current_user.role})")
        analytics = service.get_enterprise_metrics(hr_id=current_user.id if current_user.role != "admin" else None)
        
        # 2. Application Status Distribution (for Charts)
        status_query = db.query(
            Application.status, func.count(Application.id)
        ).join(Job)
        
        if current_user.role != "admin":
            status_query = status_query.filter(Job.hr_id == current_user.id)
            
        status_counts = status_query.group_by(Application.status).all()
        
        chart_data = []
        for app_status, count in status_counts:
            # Handle potential null or 'Reject' vs 'rejected'
            label = str(app_status or "Unknown").replace("_", " ").title()
            chart_data.append({"name": label, "value": count})

        # 3. Recent Activity (Filtered by HR if not admin)
        activity_query = db.query(Interview).join(Application).join(Job).options(
            joinedload(Interview.application).joinedload(Application.job)
        )
        if current_user.role != "admin":
            activity_query = activity_query.filter(Job.hr_id == current_user.id)
            
        recent_interviews = activity_query.order_by(Interview.created_at.desc()).limit(5).all()

        recent_interviews_data = []
        for interview in recent_interviews:
            recent_interviews_data.append({
                "id": interview.id,
                "candidate_name": interview.application.candidate_name if interview.application else "Unknown",
                "job_title": interview.application.job.title if interview.application and interview.application.job else "Unknown",
                "status": interview.status,
                "created_at": interview.created_at
            })

        return {
            **analytics,
            "chart_data": chart_data,
            "recent_activity": recent_interviews_data
        }
    except Exception as e:
        print(f"CRITICAL ERROR in get_dashboard_analytics: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



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

    try:
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
                        # If the stored evaluation JSON is missing structured metric keys (common when evaluation failed
                        # or older data was stored), fall back to the per-metric columns on InterviewAnswer so the
                        # frontend doesn't render all zeros.
                        base_overall = float(ans.answer_score or 0)
                        q_type_lower = (q.question_type or "technical").lower()
                        if q_type_lower == "behavioral":
                            evaluation.setdefault("relevance", float(ans.technical_score or ans.skill_relevance_score or base_overall))
                            evaluation.setdefault("action_impact", float(ans.completeness_score or base_overall))
                            evaluation.setdefault("clarity", float(ans.clarity_score or base_overall))
                        elif q_type_lower != "aptitude":
                            evaluation.setdefault("technical_accuracy", float(ans.technical_score or ans.skill_relevance_score or base_overall))
                            evaluation.setdefault("completeness", float(ans.completeness_score or base_overall))
                            evaluation.setdefault("clarity", float(ans.clarity_score or base_overall))
                            evaluation.setdefault("depth", float(ans.depth_score or base_overall))
                            evaluation.setdefault("practicality", float(ans.practicality_score or base_overall))

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

            # Calculate averages for return
            all_q = question_evaluations + aptitude_question_evaluations
            tech_s = [q.get("score", 0) for q in all_q if q.get("question_type") == "technical"]
            beh_s = [q.get("score", 0) for q in all_q if q.get("question_type") == "behavioral"]
            apt_q = aptitude_question_evaluations
            
            tech_avg = sum(tech_s) / len(tech_s) if tech_s else 0
            beh_avg = sum(beh_s) / len(beh_s) if beh_s else 0
            apt_qty = len(apt_q)
            apt_correct = sum(1 for q in apt_q if q.get("correct"))
            apt_score = (apt_correct / apt_qty * 10) if apt_qty > 0 else 0

            # Overall formatting
            created = report.created_at
            return {
                "id": report.id,
                "filename": f"report_{report.id}.json",
                "test_id": interview.test_id if interview else None,
                "timestamp": created.isoformat() if created else "",
                "display_date": created.strftime("%Y-%m-%d %H:%M:%S") if created else "",
                "display_date_short": created.strftime("%b %d, %Y") if created else "",
                "status": application.status if application else (interview.status if interview else "completed"),
                "overall_score": report.overall_score or 0,
                "final_score": report.combined_score or report.overall_score or 0,
                "technical_score": tech_avg if tech_avg > 0 else (report.technical_skills_score or 0),
                "behavioral_score": beh_avg if beh_avg > 0 else (report.behavioral_score or 0),
                "aptitude_score": apt_score if apt_score > 0 else (report.aptitude_score or 0),
                # Enterprise Scoring (Point 2)
                "resume_score": report.resume_score if hasattr(report, 'resume_score') else 0,
                "aptitude_score": report.aptitude_score if hasattr(report, 'aptitude_score') else 0,
                "interview_score": report.interview_score if hasattr(report, 'interview_score') else 0,
                "composite_score": report.composite_score if hasattr(report, 'composite_score') else 0,
                "total_questions_answered": len(question_evaluations),
                "aptitude_questions_answered": len(aptitude_question_evaluations),
                "question_evaluations": question_evaluations,
                "aptitude_question_evaluations": aptitude_question_evaluations,
                "candidate_profile": candidate_profile,
                "tech_score": report.technical_skills_score or tech_avg,
                "comm_score": report.communication_score,
                "evaluated_skills": report.evaluated_skills,
                "video_url": interview.video_recording_path if interview else None,
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
                            # Fallback chain for ID: test_id -> report_id -> id -> filename
                            t_id = data.get("test_id") or data.get("report_id") or data.get("id") or filename
                            
                            if t_id not in seen_test_ids:
                                # Calculate scores for file-based reports
                                cand = data.get("candidate_profile", {})
                                q_evals = data.get("question_evaluations", [])
                                f_apt_evals = data.get("aptitude_question_evaluations", [])
                                combined_q = q_evals + f_apt_evals
                                
                                f_tech_scores = [q.get("score", 0) for q in combined_q if q.get("question_type") == "technical"]
                                f_beh_scores = [q.get("score", 0) for q in combined_q if q.get("question_type") == "behavioral"]
                                
                                f_tech_avg = sum(f_tech_scores) / len(f_tech_scores) if f_tech_scores else 0
                                f_beh_avg = sum(f_beh_scores) / len(f_beh_scores) if f_beh_scores else 0
                                f_apt_qty = len(f_apt_evals)
                                f_apt_correct = sum(1 for q in f_apt_evals if q.get("correct"))
                                f_apt_score = (f_apt_correct / f_apt_qty * 10) if f_apt_qty > 0 else 0

                                reports.append({
                                    "id": f"file_{filename}",
                                    "filename": filename,
                                    "test_id": t_id,
                                    "timestamp": data.get("timestamp", data.get("created_at", "")),
                                    "display_date": data.get("display_date", data.get("timestamp", "")),
                                    "display_date_short": data.get("display_date_short", filename[:10]),
                                    "status": data.get("status", "completed"),
                                    "overall_score": data.get("overall_score") or data.get("final_score") or 0,
                                    "final_score": data.get("final_score") or 0,
                                    "technical_score": f_tech_avg or data.get("technical_score") or 0,
                                    "behavioral_score": f_beh_avg or data.get("behavioral_score") or 0,
                                    "aptitude_score": f_apt_score or data.get("aptitude_score") or 0,
                                    "total_questions_answered": len(q_evals),
                                    "question_evaluations": q_evals,
                                    "aptitude_question_evaluations": f_apt_evals,
                                    "candidate_profile": cand,
                                    "tech_score": data.get("tech_score") or f_tech_avg,
                                    "comm_score": data.get("comm_score"),
                                    "evaluated_skills": data.get("evaluated_skills"),
                                    "video_url": data.get("video_url"),
                                    "source": "file"
                                })
                                seen_test_ids.add(t_id)
                    except Exception as e:
                        print(f"Error reading report file {filename}: {e}")

        # Final sort - newest first
        reports.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return reports
    except Exception as e:
        print("CRITICAL ERROR in get_interview_reports:")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while fetching reports: {str(e)}"
        )



@router.get("/interviews")
async def get_filtered_interviews(
    candidate_name: Optional[str] = None,
    candidate_email: Optional[str] = None,
    test_id: Optional[str] = None,
    role_applied: Optional[str] = None,
    search: Optional[str] = None,
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

    query = db.query(Interview).join(Application).join(Job).outerjoin(InterviewReport)

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
            "status": interview.status,
            "report_id": interview.report.id if interview.report else None
        })

    return result


