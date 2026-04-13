from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_
from app.domain.models import Job, Application, Interview, InterviewReport, User
from typing import Dict, Any, List

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def get_dashboard(cls, db: Session, hr_id: int = None) -> Dict[str, Any]:
        """
        Get consistent dashboard metrics with null safety and zero defaults.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            from sqlalchemy import and_
            
            # Combine all core metrics into a single row fetch to minimize network round-trips
            metrics_query = db.query(
                func.count(Application.id).label("total_apps"),
                func.count(case((Application.status == 'hired', Application.id))).label("hired_apps"),
                func.avg(case((Application.composite_score > 0, Application.composite_score))).label("avg_score")
            )
            
            if hr_id:
                metrics_query = metrics_query.outerjoin(Job, Application.job_id == Job.id).filter(
                    or_(Job.hr_id == hr_id, Application.hr_id == hr_id)
                )
            
            m_res = metrics_query.first()
            total_applications = m_res.total_apps or 0
            hired_count = m_res.hired_apps or 0
            average_score = m_res.avg_score or 0

            # Interview stats
            int_query = db.query(
                func.count(Interview.id).label("total_ints"),
                func.count(case((Interview.status == "completed", Interview.id))).label("completed_ints")
            ).outerjoin(Application, Interview.application_id == Application.id).outerjoin(Job, Application.job_id == Job.id)

            if hr_id:
                int_query = int_query.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            
            i_res = int_query.first()
            total_interviews = i_res.total_ints or 0
            completed_interviews = i_res.completed_ints or 0
            
            success_rate = (hired_count / total_applications * 100) if total_applications > 0 else 0

            result = {
                "total_applications": total_applications,
                "total_interviews": total_interviews,
                "completed_interviews": completed_interviews,
                "success_rate": round(success_rate, 2),
                "average_score": round(float(average_score), 2)
            }
            logger.info(f"[ANALYTICS DATA] {result}")
            return result
        except Exception as e:
            logger.error(f"[ANALYTICS SERVICE ERROR] {str(e)}")
            return {
                "total_applications": 0,
                "total_interviews": 0,
                "completed_interviews": 0,
                "success_rate": 0,
                "average_score": 0
            }

    def get_enterprise_metrics(self, hr_id: int = None) -> Dict[str, Any]:
        """
        Calculate enterprise-level recruitment metrics (Point 5).
        """
        # Calculate all counts in a single query using CASE WHEN
        # Application Counts
        app_metrics = self.db.query(
            func.count(Application.id).label("total")
        ).outerjoin(Job, Application.job_id == Job.id)
        
        # Interview Counts (Valid = not_started, in_progress, completed)
        int_metrics = self.db.query(
            func.count(Interview.id).label("total"),
            func.count(case((Interview.status == "completed", Interview.id))).label("completed")
        ).join(Application, Interview.application_id == Application.id).outerjoin(Job, Application.job_id == Job.id)
        
        # Hired Count
        hired_metrics = self.db.query(func.count(Application.id)).filter(Application.status == 'hired').outerjoin(Job, Application.job_id == Job.id)

        if hr_id:
            app_metrics = app_metrics.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            int_metrics = int_metrics.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            hired_metrics = hired_metrics.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            
        total_applications = app_metrics.scalar() or 0
        valid_int_result = int_metrics.filter(Interview.status.in_(['not_started', 'in_progress', 'completed'])).first()
        valid_interviews = valid_int_result[0] if valid_int_result else 0
        completed_interviews = valid_int_result[1] if valid_int_result else 0
        hired_count = hired_metrics.scalar() or 0

        # Debug Logging for Correctness Verification
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[ANALYTICS] Accuracy Check - Total Apps: {total_applications}, Valid Ints: {valid_interviews}, Completed Ints: {completed_interviews}")

        # Validation Check
        if valid_interviews > total_applications:
            logger.warning(f"[ANALYTICS] Suspicious Data: Intervews ({valid_interviews}) exceed Applications ({total_applications})")
        if completed_interviews > valid_interviews:
            logger.error(f"[ANALYTICS] LOGIC ERROR: Completed ({completed_interviews}) exceeds Valid Total ({valid_interviews})")

        # Calculations
        completion_rate = (completed_interviews / valid_interviews * 100) if valid_interviews > 0 else 0
        hiring_success_rate = (hired_count / total_applications * 100) if total_applications > 0 else 0

        # Candidate aggregate metrics
        # Candidate aggregate metrics with COALESCE for null safety
        avg_resume_score_query = self.db.query(func.coalesce(func.avg(Application.resume_score), 0)).filter(Application.resume_score > 0).outerjoin(Job, Application.job_id == Job.id)
        avg_aptitude_score_query = self.db.query(func.coalesce(func.avg(Application.aptitude_score), 0)).filter(Application.aptitude_score > 0).outerjoin(Job, Application.job_id == Job.id)
        avg_interview_score_query = self.db.query(func.coalesce(func.avg(Application.interview_score), 0)).filter(Application.interview_score > 0).outerjoin(Job, Application.job_id == Job.id)
        avg_composite_score_query = self.db.query(func.coalesce(func.avg(Application.composite_score), 0)).filter(Application.composite_score > 0).outerjoin(Job, Application.job_id == Job.id)

        if hr_id:
            avg_resume_score_query = avg_resume_score_query.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            avg_aptitude_score_query = avg_aptitude_score_query.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            avg_interview_score_query = avg_interview_score_query.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))
            avg_composite_score_query = avg_composite_score_query.filter(or_(Job.hr_id == hr_id, Application.hr_id == hr_id))

        avg_resume_score = avg_resume_score_query.scalar() or 0
        avg_aptitude_score = avg_aptitude_score_query.scalar() or 0
        avg_interview_score = avg_interview_score_query.scalar() or 0
        avg_composite_score = avg_composite_score_query.scalar() or 0

        return {
            "recruitment_metrics": {
                "total_candidates": total_applications,
                "shortlisted_candidates": valid_interviews, # Shortlisted currently mapped to having an interview
                "interviewed_candidates": completed_interviews,
                "offers_released": hired_count,
                "hiring_success_rate": round(hiring_success_rate, 2),
                "completion_rate": round(completion_rate, 2)
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
