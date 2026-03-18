from app.services.scoring_engine.score_calculator import ScoreCalculator
from app.services.scoring_engine.feedback_generator import FeedbackGenerator
from app.services.skill_graph.skill_analyzer import SkillAnalyzer

class ReportGenerator:
    """
    Compiles the final end-to-end interview report, merging 
    composite scores, skill graph analysis, and rendering a final HIre Signal.
    """
    
    def __init__(self, db_session, session_id: str):
        self.db = db_session
        self.session_id = session_id
        self.skill_analyzer = SkillAnalyzer(db_session, session_id)

    def generate_final_report(self, all_evaluations: list[dict]) -> dict:
        """
        Calculates final scores and makes STRONG_HIRE, HIRE, HOLD, NO_HIRE recommendations.
        """
        # 1. Get Composite Scores
        composite_scores = ScoreCalculator.calculate_composite_score(all_evaluations)
        final_score = composite_scores.get("final_score", 0.0)
        
        # 2. Get Skill Graph Analysis
        skill_analysis = self.skill_analyzer.analyze()
        strengths = skill_analysis.get("strengths", [])
        weaknesses = skill_analysis.get("weaknesses", [])
        
        # 3. Generate Executive Summary Feedback
        executive_summary = FeedbackGenerator.generate_final_feedback(all_evaluations, strengths, weaknesses)
        
        # 4. Recommendation Logic (FAANG style calibration)
        if final_score >= 8.5 and len(strengths) >= 2:
            recommendation = "STRONG_HIRE"
        elif final_score >= 7.0:
            recommendation = "HIRE"
        elif final_score >= 5.0:
            recommendation = "HOLD"
        else:
            recommendation = "NO_HIRE"
        
        report = {
            "session_id": self.session_id,
            "final_score": final_score,
            "technical_score": composite_scores.get("technical_avg", 0.0),
            "communication_score": composite_scores.get("communication_avg", 0.0),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "executive_summary": executive_summary,
            "hiring_recommendation": recommendation
        }
        
        # In a real app, save `report` to `interview_reports` DB table here.
        print(f"[ReportGenerator] Finished Report. Recommendation: {recommendation}")
        
        return report
