import logging

logger = logging.getLogger(__name__)

def adjust_difficulty(current_difficulty: str, latest_score: float) -> str:
    """
    Adaptive Interview Logic with stability guardrails.
    Ensures difficulty transitions are smooth and prevents aggressive jumping.
    """
    # 1. Input Sanitization
    try:
        score = float(latest_score)
    except (ValueError, TypeError):
        logger.warning(f"Invalid score for adjustment: {latest_score}. Keeping {current_difficulty}")
        return current_difficulty

    valid_difficulties = ["easy", "medium", "hard"]
    curr = str(current_difficulty).lower()
    
    if curr not in valid_difficulties:
        logger.warning(f"Invalid current difficulty: {current_difficulty}. Defaulting to medium")
        curr = "medium"

    # 2. Transition Logic (Step-based)
    if score >= 8.0:
        if curr == "easy":
            logger.info("Adaptive: Score high. Moving Easy -> Medium")
            return "medium"
        elif curr == "medium":
            logger.info("Adaptive: Score high. Moving Medium -> Hard")
            return "hard"
        return "hard"
            
    elif score <= 4.0:
        if curr == "hard":
            logger.info("Adaptive: Score low. Moving Hard -> Medium")
            return "medium"
        elif curr == "medium":
            logger.info("Adaptive: Score low. Moving Medium -> Easy")
            return "easy"
        return "easy"
            
    # 3. Stability (Keep current if score is 4.0 - 8.0)
    return curr
