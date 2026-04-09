from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.infrastructure.database import get_db
from app.domain.models import Application, ResumeExtraction, Job
from app.core.auth import get_current_hr
from app.services.ai_service import decompose_search_query
from sqlalchemy import or_, and_, func

router = APIRouter(prefix="/api/search", tags=["search"])

@router.post("/candidates")
async def search_candidates(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_hr = Depends(get_current_hr)
):
    """
    Search candidates using natural language query.
    Converts query text into structured SQLAlchemy filters using AI decomposition.
    """
    query_text = payload.get("query")
    skip = int(payload.get("skip", 0))
    limit = int(payload.get("limit", 30))
    
    if not query_text:
        raise HTTPException(status_code=400, detail="Search query is required")

    # 1. Decompose Query using AI
    # This maps "Python developer with leadership" -> structured metrics
    filters = await decompose_search_query(query_text)
    
    # 2. Build SQLAlchemy Query with relationship graph
    query = db.query(Application).join(Application.resume_extraction).join(Application.job).options(
        joinedload(Application.resume_extraction),
        joinedload(Application.job)
    )
    
    # Scoping: HR searches their own, Super-Admin searches all
    if current_hr.role != 'super_admin':
        query = query.filter(Application.hr_id == current_hr.id)
    
    # Respect State Machine: Default to excluding rejected candidates unless requested
    from app.services.state_machine import CandidateState
    if not filters.get("include_rejected"):
        query = query.filter(Application.status != CandidateState.REJECTED.value)
        
    keyword_conditions = []
    
    # Technical Skills matching
    tech_skills = filters.get("tech_skills", [])
    if tech_skills:
        for skill in tech_skills:
            keyword_conditions.append(or_(
                ResumeExtraction.extracted_skills.ilike(f"%{skill}%"),
                ResumeExtraction.extracted_text.ilike(f"%{skill}%"),
                Job.title.ilike(f"%{skill}%")
            ))
            
    # Soft Skills / Leadership matching
    soft_skills = filters.get("soft_skills", [])
    if soft_skills:
        for skill in soft_skills:
            keyword_conditions.append(or_(
                ResumeExtraction.summary.ilike(f"%{skill}%"),
                ResumeExtraction.extracted_text.ilike(f"%{skill}%")
            ))
            
    # Experience Level mapping
    exp_level = filters.get("experience_level")
    if exp_level:
        query = query.filter(ResumeExtraction.experience_level == exp_level)
            
    # Handle Experience Range
    min_exp = filters.get("min_experience_years")
    if min_exp is not None:
        query = query.filter(ResumeExtraction.years_of_experience >= float(min_exp))
        
    max_exp = filters.get("max_experience_years")
    if max_exp is not None:
        query = query.filter(ResumeExtraction.years_of_experience <= float(max_exp))
        
    # Role Keywords (e.g. "Senior", "Architect")
    role_keywords = filters.get("role_keywords", [])
    if role_keywords:
        for keyword in role_keywords:
            keyword_conditions.append(or_(
                ResumeExtraction.previous_roles.ilike(f"%{keyword}%"),
                ResumeExtraction.summary.ilike(f"%{keyword}%"),
                Application.candidate_name.ilike(f"%{keyword}%"),
                Job.title.ilike(f"%{keyword}%")
            ))
            
    # Apply combined keyword and skill filters
    if keyword_conditions:
        query = query.filter(and_(*keyword_conditions))
        
    # 3. Retrieve and Rank with Pagination
    total = query.count()
    results = query.order_by(Application.composite_score.desc()).offset(skip).limit(limit).all()

    # BROAD FALLBACK: If AI-driven filters yield 0 results, try a simple global keyword match
    is_fallback = False
    if not results and query_text:
        # Re-build generic query without complex AI filters
        fallback_query = db.query(Application).join(Application.resume_extraction).join(Application.job).options(
            joinedload(Application.resume_extraction),
            joinedload(Application.job)
        )
        if current_hr.role != 'super_admin':
            fallback_query = fallback_query.filter(Application.hr_id == current_hr.id)
            
        # Search query text anywhere in name, skills, or job title
        fallback_query = fallback_query.filter(or_(
            Application.candidate_name.ilike(f"%{query_text}%"),
            ResumeExtraction.extracted_skills.ilike(f"%{query_text}%"),
            ResumeExtraction.extracted_text.ilike(f"%{query_text}%"),
            Job.title.ilike(f"%{query_text}%")
        ))
        total = fallback_query.count()
        results = fallback_query.offset(skip).limit(limit).all()
        is_fallback = True
    
    # 4. Format detailed results with Match Insights
    search_results = []
    for app in results:
        search_results.append({
            "id": app.id,
            "candidate_name": app.candidate_name,
            "current_status": app.status,
            "job_title": app.job.title if app.job else "General Portfolio",
            "resume_score": app.resume_score,
            "composite_score": app.composite_score,
            "years_of_experience": app.resume_extraction.years_of_experience if app.resume_extraction else 0,
            "match_insight": app.resume_extraction.reasoning if app.resume_extraction else "Historical record matches core skills.",
            "skills": app.resume_extraction.extracted_skills if app.resume_extraction else "[]"
        })
        
    return {
        "metadata": {
            "original_query": query_text,
            "interpreted_filters": filters,
            "total": total,
            "skip": skip,
            "limit": limit,
            "found_count": len(search_results),
            "is_fallback": is_fallback
        },
        "candidates": search_results
    }
