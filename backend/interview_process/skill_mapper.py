try:
    from .config import SKILL_CATEGORIES
except ImportError:
    from config import SKILL_CATEGORIES

def map_skills_to_category(detected_skills: list[str]) -> str:
    scores = {cat: 0 for cat in SKILL_CATEGORIES}

    for skill in detected_skills:
        s = skill.lower()
        for cat, keywords in SKILL_CATEGORIES.items():
            for k in keywords:
                if k.lower() in s:
                    scores[cat] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "backend"
