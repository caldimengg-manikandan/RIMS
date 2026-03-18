from app.services.difficulty_engine.question_selector import QuestionSelector
from app.services.difficulty_engine.difficulty_engine import adjust_difficulty

class QuestionController:
    """
    Orchestrates logic to determine the next best question 
    using the Difficulty Engine.
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.selector = QuestionSelector(db_session)

    def select_first_question(self, job_domain: str) -> dict:
        """
        Selecting the first introductory question, typically medium difficulty.
        """
        return self.selector.select_next_question(domain=job_domain, difficulty="medium", asked_ids=[])

    def generate_next_question(self, session_data: dict, last_answer_score: float) -> dict:
        """
        Determines the next question based on the candidate's last answer score.
        """
        current_diff = session_data.get("current_difficulty", "medium")
        new_diff = adjust_difficulty(current_diff, last_answer_score)
        
        # Update session state with new difficulty trajectory
        session_data["current_difficulty"] = new_diff
        
        return self.selector.select_next_question(domain="General", difficulty=new_diff, asked_ids=[])
