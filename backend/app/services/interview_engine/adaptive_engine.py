import logging

logger = logging.getLogger(__name__)

def adjust_difficulty(current_difficulty: str, latest_score: float) -> str:
    """
    Adaptive Interview Logic
    Adjusts the difficulty of the next question based on the candidate's recent performance.
    """
    if latest_score >= 8.0:
        if current_difficulty == "easy":
            return "medium"
        elif current_difficulty == "medium":
            return "hard"
        else:
            return "hard" # Cap
            
    elif latest_score <= 4.0:
        if current_difficulty == "hard":
            return "medium"
        elif current_difficulty == "medium":
            return "easy"
        else:
            return "easy" # Cap
            
    # Keep current difficulty if score is average
    return current_difficulty
