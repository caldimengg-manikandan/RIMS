class SkillAnalyzer:
    """
    Analyzes the complete skill graph to extract strengths,
    weaknesses, and generate high-level hiring signals.
    """
    
    def __init__(self, db_session, session_id: int):
        self.db = db_session
        self.session_id = session_id

    def analyze(self) -> dict:
        """
        Returns the top 3 strengths and bottom 3 weaknesses based 
        on the finalized skill graph scores.
        """
        # In a real app, this queries all CandidateSkills for the session
        mock_graph = {
            "Python": 85,
            "SQL": 70,
            "System Design": 45,
            "Communication": 90,
            "Debugging": 60
        }
        
        sorted_skills = sorted(mock_graph.items(), key=lambda x: x[1], reverse=True)
        
        strengths = [s[0] for s in sorted_skills[:3] if s[1] >= 75]
        weaknesses = [s[0] for s in sorted_skills[-3:] if s[1] < 60]
        
        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "overall_technical_health": "Strong" if len(strengths) > len(weaknesses) else "Needs Improvement"
        }
