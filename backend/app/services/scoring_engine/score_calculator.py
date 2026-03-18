class ScoreCalculator:
    """
    Computes and normalizes composite scores across an entire interview session.
    """
    
    @staticmethod
    def calculate_composite_score(evaluations: list[dict]) -> dict:
        """
        Takes a list of individual answer evaluations and aggregates them
        into a final session composite score.
        """
        if not evaluations:
            return {"final_score": 0.0, "technical_avg": 0.0, "communication_avg": 0.0}

        total_tech = sum(e.get("technical_score", 0) for e in evaluations)
        total_comm = sum(e.get("communication_score", 0) for e in evaluations)
        total_conf = sum(e.get("confidence_score", 0) for e in evaluations)
        total_corr = sum(e.get("correctness_score", 0) for e in evaluations)
        
        n = len(evaluations)
        
        avg_tech = total_tech / n
        avg_comm = total_comm / n
        avg_conf = total_conf / n
        avg_corr = total_corr / n
        
        # Weighted final score (FAANG style emphasizing tech and correctness)
        final_score = (avg_tech * 0.4) + (avg_corr * 0.4) + (avg_comm * 0.15) + (avg_conf * 0.05)
        
        return {
            "final_score": round(final_score, 2),
            "technical_avg": round(avg_tech, 2),
            "communication_avg": round(avg_comm, 2),
            "confidence_avg": round(avg_conf, 2),
            "correctness_avg": round(avg_corr, 2)
        }
