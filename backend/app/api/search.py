from fastapi import APIRouter, Depends, HTTPException, Body
try:
    import orjson
    from fastapi.responses import ORJSONResponse
except ImportError:
    from fastapi.responses import JSONResponse as ORJSONResponse
from sqlalchemy.orm import Session, joinedload, load_only, defer
from typing import List, Optional, Any
from app.infrastructure.database import get_db
from app.domain.models import Application, ResumeExtraction, Job
from app.core.auth import get_current_hr
from app.services.ai_service import decompose_search_query
from sqlalchemy import or_, and_, func
from app.core.storage import get_signed_url
from app.core.config import get_settings
import logging
logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter(prefix="/api/search", tags=["search"])

@router.post("/candidates")
async def search_candidates(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_hr = Depends(get_current_hr)
):
    query_text = payload.get("query")
    skip = int(payload.get("skip", 0))
    limit = int(payload.get("limit", 30))
    if not query_text: raise HTTPException(status_code=400, detail="Search query is required")
    
    try:
        filters = await decompose_search_query(query_text)
        query = db.query(Application).options(
            joinedload(Application.resume_extraction).load_only(
                ResumeExtraction.id, ResumeExtraction.resume_score, ResumeExtraction.skill_match_percentage, ResumeExtraction.experience_level,
                ResumeExtraction.summary, ResumeExtraction.extracted_skills, ResumeExtraction.years_of_experience, ResumeExtraction.reasoning, ResumeExtraction.previous_roles
            ),
            joinedload(Application.job).load_only(Job.id, Job.title, Job.job_id),
            joinedload(Application.hr).load_only(User.id, User.full_name),
            load_only(Application.id, Application.candidate_name, Application.status, Application.applied_at, Application.composite_score, Application.resume_score, Application.file_status, Application.candidate_photo_path, Application.hr_id),
            defer(Application.candidate_phone), defer(Application.hr_notes)
        )
        # Apply visibility isolation: Anyone not a super_admin is restricted to their own data
        if current_hr.role.lower() != "super_admin":
            query = query.join(Application.job)
            query = query.filter(or_(Job.hr_id == current_hr.id, Application.hr_id == current_hr.id))
        # Super Admin sees all.
        
        keyword_conditions = []
        for field in ["tech_skills", "soft_skills", "role_keywords"]:
            for val in filters.get(field, []):
                keyword_conditions.append(or_(ResumeExtraction.extracted_skills.ilike(f"%{val}%"), ResumeExtraction.extracted_text.ilike(f"%{val}%"), Job.title.ilike(f"%{val}%")))
        if keyword_conditions: query = query.filter(and_(*keyword_conditions))
        
        total = query.count()
        results = query.order_by(Application.composite_score.desc()).offset(skip).limit(limit).all()
        
        search_results = []
        for app in results:
            search_results.append({
                "id": app.id, "candidate_name": app.candidate_name, "current_status": app.status,
                "job_title": app.job.title if app.job else "General Portfolio", "job_id": app.job.job_id if app.job else "N/A",
                "resume_score": max(0.0, min(100.0, app.resume_score or 0.0)), "composite_score": max(0.0, min(100.0, app.composite_score or 0.0)),
                "years_of_experience": app.resume_extraction.years_of_experience if app.resume_extraction else 0,
                "match_insight": app.resume_extraction.reasoning if app.resume_extraction else "Historical match.",
                "skills": app.resume_extraction.extracted_skills if app.resume_extraction else "[]",
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "file_status": app.file_status,
                "assigned_hr_id": app.hr_id,
                "assigned_hr_name": app.hr.full_name if app.hr else "Unknown",
                "is_owner": (app.hr_id == current_hr.id)
            })
        return {"items": search_results, "total": total}
    except Exception as e:
        import logging; logger = logging.getLogger(__name__)
        logger.error(f"SEARCH_API_ERROR: {str(e)}", exc_info=True)
        return {"metadata": {"total": 0, "error_hint": str(e)}, "candidates": []}
