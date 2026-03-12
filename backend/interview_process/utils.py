import re
from typing import Dict, List, Tuple

def format_response(text: str, color: str = None) -> str:
    """Format text (color argument is ignored for compatibility)"""
    return text
def extract_skills(text: str) -> List[str]:
    """Extract technical skills from text using config (Dynamic)"""
    try:
        from .config import SKILL_CATEGORIES
    except ImportError:
        return []

    found_skills = []
    text_lower = text.lower()
    
    # Iterate through all categories in config
    for category, keywords in SKILL_CATEGORIES.items():
        for keyword in keywords:
            # Check for keyword in text (case insensitive)
            if keyword.lower() in text_lower:
                found_skills.append(keyword)
    
    # Remove duplicates while preserving order
    unique_skills = []
    seen = set()
    for skill in found_skills:
        skill_clean = skill.strip()
        if skill_clean.lower() not in seen:
            seen.add(skill_clean.lower())
            unique_skills.append(skill_clean)
            
    return unique_skills

def calculate_performance_score(responses: List[Dict]) -> float:
    """Calculate candidate performance score"""
    if not responses:
        return 0.0
    
    scores = []
    for response in responses:
        score = response.get('score', 0)
        scores.append(score)
    
    return sum(scores) / len(scores)

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

# Add these new functions to utils.py

def calculate_detailed_score(responses: List[Dict]) -> Dict:
    """Calculate detailed performance scores"""
    if not responses:
        return {
            "overall": 0,
            "technical": 0,
            "behavioral": 0,
            "clarity": 0,
            "depth": 0
        }
    
    scores = {
        "overall": [],
        "technical": [],
        "behavioral": [],
        "clarity": [],
        "depth": []
    }
    
    for response in responses:
        eval_data = response.get('evaluation', {})
        scores["overall"].append(eval_data.get('overall', 5))
        scores["technical"].append(eval_data.get('accuracy', 5))
        scores["behavioral"].append(eval_data.get('relevance', 5))
        scores["clarity"].append(eval_data.get('relevance', 5))  # Using relevance for clarity
        scores["depth"].append(eval_data.get('depth', 5))
    
    # Calculate averages
    result = {}
    for key, value in scores.items():
        if value:  # Check if list is not empty
            result[key] = sum(value) / len(value)
        else:
            result[key] = 0
    
    return result

def analyze_response_quality(response_text: str) -> Dict:
    """Analyze response quality metrics"""
    words = response_text.split()
    word_count = len(words)
    
    # Calculate various metrics
    metrics = {
        "word_count": word_count,
        "has_technical_terms": any(term in response_text.lower() for term in 
                                   ["api", "database", "system", "design", "algorithm", "architecture"]),
        "has_examples": any(indicator in response_text.lower() for indicator in 
                           ["for example", "for instance", "such as", "like"]),
        "has_explanation": any(indicator in response_text for indicator in 
                              ["because", "therefore", "thus", "so", "since"]),
        "sentence_count": len([s for s in response_text.split('.') if s.strip()]),
        "avg_sentence_length": word_count / max(1, len([s for s in response_text.split('.') if s.strip()]))
    }
    
    return metrics

def get_performance_feedback(avg_score: float, detailed_scores: Dict) -> str:
    """Generate performance feedback based on scores"""
    if avg_score >= 8.5:
        return "Excellent - Demonstrates deep understanding and clear communication"
    elif avg_score >= 7.0:
        return "Good - Shows solid understanding with room for refinement"
    elif avg_score >= 5.5:
        return "Average - Basic understanding but lacks depth in some areas"
    elif avg_score >= 4.0:
        return "Below Average - Struggles with technical concepts"
    else:
        return "Poor - Significant gaps in knowledge and communication"

def format_score_bar(score: float, max_score: float = 10) -> str:
    """Create a visual score bar"""
    bars = int((score / max_score) * 20)
    bar = "█" * bars + "░" * (20 - bars)
    return f"{bar} {score:.1f}/10"

# Add to utils.py

def analyze_technical_content(answer: str) -> Dict:
    """Analyze technical content of an answer"""
    technical_indicators = {
        "architecture_terms": ["microservices", "monolithic", "scalable", "distributed", "load balancing"],
        "coding_terms": ["algorithm", "data structure", "time complexity", "space complexity", "optimization"],
        "system_design": ["database", "cache", "API", "endpoint", "protocol", "authentication"],
        "problem_solving": ["approach", "solution", "alternative", "trade-off", "consideration"]
    }
    
    result = {}
    answer_lower = answer.lower()
    
    for category, terms in technical_indicators.items():
        found_terms = [term for term in terms if term in answer_lower]
        result[category] = {
            "count": len(found_terms),
            "terms": found_terms
        }
    
    return result

def generate_strengths_analysis(responses: List[Dict]) -> List[str]:
    """Generate strengths analysis based on responses"""
    strengths = []
    
    if not responses:
        return ["No responses to analyze"]
    
    # Analyze technical depth
    high_depth_responses = [r for r in responses if r.get('evaluation', {}).get('depth', 0) >= 7]
    if len(high_depth_responses) >= len(responses) * 0.4:
        strengths.append("Demonstrates good technical depth in responses")
    
    # Analyze clarity
    high_clarity_responses = [r for r in responses if r.get('evaluation', {}).get('clarity', 0) >= 7]
    if len(high_clarity_responses) >= len(responses) * 0.4:
        strengths.append("Communicates technical concepts clearly")
    
    # Check for examples
    responses_with_examples = 0
    for response in responses:
        answer = response.get('answer', '')
        if any(indicator in answer.lower() for indicator in ['for example', 'for instance', 'in my project', 'i implemented']):
            responses_with_examples += 1
    
    if responses_with_examples >= len(responses) * 0.3:
        strengths.append("Effectively uses real-world examples")
    
    # Check response length consistency
    word_counts = [r.get('word_count', 0) for r in responses if r.get('word_count', 0) > 0]
    if word_counts:
        avg_words = sum(word_counts) / len(word_counts)
        if 80 <= avg_words <= 200:
            strengths.append("Maintains appropriate response length")
    
    return strengths[:3]  # Return top 3 strengths

def generate_weaknesses_analysis(responses: List[Dict]) -> List[str]:
    """Generate weaknesses analysis based on responses"""
    weaknesses = []
    
    if len(responses) <= 1:
        return ["Insufficient responses for detailed analysis"]
    
    # Check for low scores in key areas
    low_accuracy = [r for r in responses if r.get('evaluation', {}).get('technical_accuracy', 0) < 5]
    if len(low_accuracy) >= len(responses) * 0.3:
        weaknesses.append("Needs improvement in technical accuracy")
    
    low_completeness = [r for r in responses if r.get('evaluation', {}).get('completeness', 0) < 5]
    if len(low_completeness) >= len(responses) * 0.3:
        weaknesses.append("Answers sometimes lack completeness")
    
    # Check for short responses
    short_responses = [r for r in responses if r.get('word_count', 0) < 60 and r.get('question_type') != 'intro']
    if len(short_responses) >= len(responses) * 0.3:
        weaknesses.append("Some responses could be more detailed")
    
    # Check score consistency
    scores = [r.get('score', 0) for r in responses]
    if scores and max(scores) - min(scores) > 4:
        weaknesses.append("Performance varies significantly across questions")
    
    return weaknesses[:3]  # Return top 3 weaknesses

def calculate_recommendation(avg_score: float, responses: List[Dict]) -> str:
    """Calculate recommendation based on scores and responses"""
    
    if len(responses) <= 1:
        return "INCONCLUSIVE - Insufficient data"
    
    # Get technical and behavioral scores separately
    tech_responses = [r for r in responses if r.get('question_type') == 'technical']
    behavioral_responses = [r for r in responses if r.get('question_type') == 'behavioral']
    
    tech_score = 0
    if tech_responses:
        tech_score = sum(r.get('score', 0) for r in tech_responses) / len(tech_responses)
    
    behavioral_score = 0
    if behavioral_responses:
        behavioral_score = sum(r.get('score', 0) for r in behavioral_responses) / len(behavioral_responses)
    
    # Decision matrix
    if avg_score >= 8.0 and tech_score >= 7.5:
        return "STRONGLY ACCEPT - Excellent technical and communication skills"
    elif avg_score >= 7.0 and tech_score >= 6.5:
        return "ACCEPT - Strong candidate with good fundamentals"
    elif avg_score >= 6.0 and tech_score >= 5.5:
        return "CONDITIONAL ACCEPT - Shows potential with some areas to improve"
    elif avg_score >= 5.0:
        return "RECONSIDER AFTER IMPROVEMENT - Needs work on core technical areas"
    else:
        return "REJECT - Does not meet minimum technical requirements"