from sqlalchemy.orm import Session
from sqlalchemy import func
from app.domain.models import Job, Application, Interview, InterviewReport, User
from typing import Dict, Any, List

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_enterprise_metrics(self, hr_id: int = None) -> Dict[str, Any]:
        """
        Calculate enterprise-level recruitment metrics (Point 5).
        """
        # Calculate all counts in a single query using CASE WHEN
        from sqlalchemy import case
        metrics = self.db.query(
            func.count(Application.id).label("total"),
            func.count(case((Application.status.in_([
                'aptitude_round', 'ai_interview', 'ai_interview_completed', 
                'review_later', 'physical_interview', 'hired', 'rejected'
            ]), Application.id))).label("shortlisted"),
            func.count(case((Application.status.in_([
                'ai_interview', 'ai_interview_completed', 'physical_interview', 'hired'
            ]), Application.id))).label("interviewed"),
            func.count(case((Application.status == 'hired', Application.id))).label("hired")
        ).outerjoin(Job)
        
        if hr_id:
            from sqlalchemy import or_
            metrics = metrics.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            
        total_candidates, shortlisted, interviewed, offers_released = metrics.first()
        
        hiring_success_rate = (offers_released / total_candidates * 100) if total_candidates > 0 else 0

        # Candidate aggregate metrics
        avg_resume_score = self.db.query(func.avg(Application.resume_score)).filter(Application.resume_score > 0).scalar() or 0
        avg_aptitude_score = self.db.query(func.avg(Application.aptitude_score)).filter(Application.aptitude_score > 0).scalar() or 0
        avg_interview_score = self.db.query(func.avg(Application.interview_score)).filter(Application.interview_score > 0).scalar() or 0
        avg_composite_score = self.db.query(func.avg(Application.composite_score)).filter(Application.composite_score > 0).scalar() or 0

        return {
            "recruitment_metrics": {
                "total_candidates": total_candidates,
                "shortlisted_candidates": shortlisted,
                "interviewed_candidates": interviewed,
                "offers_released": offers_released,
                "hiring_success_rate": round(hiring_success_rate, 2)
            },
            "candidate_metrics": {
                "avg_job_compatibility": round(avg_resume_score, 2),
                "avg_aptitude_score": round(avg_aptitude_score, 2),
                "avg_interview_score": round(avg_interview_score, 2),
                "avg_composite_score": round(avg_composite_score, 2)
            }
        }

    def get_job_pipeline_stats(self, job_id: int) -> List[Dict[str, Any]]:
        """
        Get count of candidates in each stage for a specific job (Point 12).
        """
        stages = [
            'applied', 'aptitude_round', 'ai_interview', 'ai_interview_completed',
            'review_later', 'physical_interview', 'hired', 'rejected'
        ]
        # Calculate all stage counts in a single GROUP BY query
        results = self.db.query(
            Application.status, 
            func.count(Application.id)
        ).filter(Application.job_id == job_id).group_by(Application.status).all()
        
        counts_map = {status: count for status, count in results}
        
        stats = []
        for stage in stages:
            stats.append({"stage": stage, "count": counts_map.get(stage, 0)})
            
        return stats
