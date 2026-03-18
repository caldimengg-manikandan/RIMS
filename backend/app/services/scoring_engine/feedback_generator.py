class FeedbackGenerator:
    """
    Synthesizes atomic feedback fragments into cohesive hiring narratives.
    """
    
    @staticmethod
    def generate_final_feedback(evaluations: list[dict], strengths: list[str], weaknesses: list[str]) -> str:
        """
        Combines individual feedback traces and aggregated strengths/weaknesses
        into a finalized executive summary for the Hiring Manager.
        """
        base_feedback = "The candidate demonstrated solid baseline knowledge. "
        
        if strengths:
            base_feedback += f"Key Strengths: {', '.join(strengths[:3])}. "
            
        if weaknesses:
            base_feedback += f"Areas for Improvement: {', '.join(weaknesses[:3])}. "
            
        base_feedback += "\nDetailed Breakdown:\n"
        for i, eval_obj in enumerate(evaluations):
            base_feedback += f"Q{i+1}: {eval_obj.get('feedback', '')}\n"
            
        return base_feedback.strip()
