from sqlalchemy.orm import Session
from app.domain.models import Application, ApplicationStage, User, AuditLog
from datetime import datetime
import json

class CandidateService:
    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(self, user_id: int, action: str, resource_type: str, resource_id: int, details: dict = None, is_critical: bool = False):
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            is_critical=is_critical
        )
        self.db.add(log)
        self.db.flush() # Keep in same transaction (Phase 8 Fix)

    def advance_stage(self, application_id: int, stage_name: str, status: str = 'pending', score: float = None, notes: str = None, evaluator_id: int = None):
        """Advance a candidate to a new pipeline stage"""
        application = self.db.query(Application).filter(Application.id == application_id).with_for_update().first() # Phase 3 Fix
        if not application:
            return None

        # Update application status to the programmatic name of the stage
        status_map = {
            "Application Submitted": "applied",
            "Resume Screening": "applied",
            "Aptitude Round": "aptitude_round",
            "Automated AI Interview": "ai_interview",
            "AI Interview Completed": "ai_interview_completed",
            "Review Later": "review_later",
            "Physical Interview": "physical_interview",
            "Hired": "hired",
            "Rejected": "rejected"
        }
        
        if stage_name in status_map:
            application.status = status_map[stage_name]

        # Create or update the stage record
        stage = self.db.query(ApplicationStage).filter(
            ApplicationStage.application_id == application_id,
            ApplicationStage.stage_name == stage_name
        ).first()

        if not stage:
            stage = ApplicationStage(
                application_id=application_id,
                stage_name=stage_name,
                started_at=datetime.utcnow()
            )
            self.db.add(stage)

        stage.stage_status = status
        if score is not None:
            stage.score = score
        if notes:
            stage.evaluation_notes = notes
        if evaluator_id:
            stage.evaluator_id = evaluator_id
        
        if status in ['pass', 'fail', 'hold']:
            stage.completed_at = datetime.utcnow()
        
        # Trigger composite score update if scores changed
        self.update_composite_score(application_id)
        
        # Combined log (Phase 8 Fix)
        self.create_audit_log(
            evaluator_id, 
            "STAGE_TRANSITION", 
            "Application", 
            application_id, 
            {"stage": stage_name, "status": status}, 
            is_critical=(status in ['pass', 'fail', 'hired'])
        )
        
        self.db.flush()
        return stage

    def update_composite_score(self, application_id: int):
        """
        Calculate: 40% Resume + 30% Aptitude + 30% Interview (First Level)
        """
        application = self.db.query(Application).filter(Application.id == application_id).with_for_update().first() # Phase 3 Fix
        if not application:
            return

        # Resume score is out of 10 in DB normally, convert to match percentage 0-100 scale
        r_val = application.resume_score or 0
        res_score = (r_val * 10) if r_val <= 10 else r_val
        
        apt_score = application.aptitude_score or 0
        int_score = application.interview_score or 0 

        # Weighted calculation
        # Final Score = 0.4*R + 0.3*A + 0.3*I
        final_score = (0.4 * res_score) + (0.3 * apt_score) + (0.3 * int_score)
        
        application.composite_score = round(final_score, 2)

        # Update recommendation based on score (Point 4)
        if final_score >= 80:
            application.recommendation = "Strong Hire"
        elif final_score >= 65:
            application.recommendation = "Hire"
        elif final_score >= 50:
            application.recommendation = "Borderline"
        else:
            application.recommendation = "Reject"

        self.db.flush()

    def get_ranked_candidates(self, job_id: int):
        """Get candidates ranked by composite score for a specific job (Point 3)"""
        return self.db.query(Application).filter(
            Application.job_id == job_id
        ).order_by(Application.composite_score.desc()).all()
