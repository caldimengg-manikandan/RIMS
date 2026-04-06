import logging

logger = logging.getLogger(__name__)

class SkillUpdater:
    """
    Updates specific nodes in the candidate's skill graph
    based on the real-time AI evaluation of their answers.
    """
    
    def __init__(self, db_session, session_id: int):
        self.db = db_session
        self.session_id = session_id

    def update_skill(self, skill_name: str, answer_score: float, difficulty: str):
        """
        Applies a weighted update to a specific skill score.
        A correct answer on a hard question boosts the score more
        than a correct answer on an easy question.
        
        Args:
            skill_name: The name of the skill (e.g., "Python")
            answer_score: The LLM evaluation score (0.0 to 10.0)
            difficulty: "easy", "medium", "hard", "expert"
        """
        weight_map = {
            "easy": 0.5,
            "medium": 1.0,
            "hard": 1.5,
            "expert": 2.0
        }
        weight = weight_map.get(difficulty.lower(), 1.0)
        
        # Calculate delta. Expected average score is 5.0
        # Positive if > 5.0, negative if < 5.0
        score_delta = (answer_score - 5.0) * weight
        
        # In a real app, query current score, add delta, clamp between 0 and 100, and save.
        # current_score = self.db.query(CandidateSkill)...
        # new_score = max(0, min(100, current_score + score_delta))
        # self.db.commit()
        
        logger.info(f"[SkillGraph] Updated {skill_name} by {score_delta:+.2f} points.")
