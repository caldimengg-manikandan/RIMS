def adjust_difficulty(current_difficulty: str, ai_score: float) -> str:
    """
    Adjusts the question difficulty based on the real-time AI evaluation score.
    Logic mapping:
      score >= 8.0     -> Ascend difficulty up to "expert"
      5.0 <= score < 8.0 -> Maintain current difficulty
      score < 5.0      -> Descend difficulty down to "easy"
    """
    hierarchy = ["easy", "medium", "hard", "expert"]
    try:
        current_idx = hierarchy.index(current_difficulty.lower())
    except ValueError:
        current_idx = 1  # Default to medium if unknown

    if ai_score >= 8.0:
        new_idx = min(current_idx + 1, len(hierarchy) - 1)
    elif ai_score < 5.0:
        new_idx = max(current_idx - 1, 0)
    else:
        new_idx = current_idx

    return hierarchy[new_idx]
