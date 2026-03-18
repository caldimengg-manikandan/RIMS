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
        query_base = self.db.query(Application).join(Job)
        if hr_id:
            query_base = query_base.filter(Job.hr_id == hr_id)

        total_candidates = query_base.count()
        
        # Shortlisted = Success in initial screening (Aptitude, AI Int, etc.)
        shortlisted = query_base.filter(Application.status.in_([
            'aptitude_round', 'ai_interview', 'ai_interview_completed', 
            'review_later', 'physical_interview', 'hired', 'rejected'
        ])).count()
        
        # Interviewed = Participated in at least one interview stage
        interviewed = query_base.filter(Application.status.in_([
            'ai_interview', 'ai_interview_completed', 'physical_interview', 'hired'
        ])).count()
        
        offers_released = query_base.filter(Application.status == 'hired').count()
        
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
        
        stats = []
        for stage in stages:
            count = self.db.query(Application).filter(
                Application.job_id == job_id,
                Application.status == stage
            ).count()
            stats.append({"stage": stage, "count": count})
            
        return stats
