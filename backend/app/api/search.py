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
    if not query_text:
        raise HTTPException(status_code=400, detail="Search query is required")

    # 1. Decompose Query using AI
    # This maps "Python developer with leadership" -> structured metrics
    filters = await decompose_search_query(query_text)
    
    # 2. Build SQLAlchemy Query with relationship graph
    query = db.query(Application).join(Application.resume_extraction).options(
        joinedload(Application.resume_extraction),
        joinedload(Application.job)
    )
    
    # Filter by user's candidates unless super_admin (keeping it simple for HR search)
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
            # Match against extracted skill JSON array or the raw text
            keyword_conditions.append(or_(
                ResumeExtraction.extracted_skills.ilike(f"%{skill}%"),
                ResumeExtraction.extracted_text.ilike(f"%{skill}%")
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
                ResumeExtraction.summary.ilike(f"%{keyword}%")
            ))
            
    # Apply combined keyword and skill filters
    if keyword_conditions:
        query = query.filter(and_(*keyword_conditions))
        
    # 3. Retrieve and Rank 
    # Prioritizing candidates that were already scored highly during extraction
    results = query.order_by(Application.composite_score.desc()).limit(30).all()
    
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
            # Critical Task Requirement: Highlighting WHY they matched
            "match_insight": app.resume_extraction.reasoning if app.resume_extraction else "Historical record matches core skills.",
            "skills": app.resume_extraction.extracted_skills if app.resume_extraction else "[]"
        })
        
    return {
        "metadata": {
            "original_query": query_text,
            "interpreted_filters": filters,
            "found_count": len(search_results)
        },
        "candidates": search_results
    }
