from openai import OpenAI
import re
from typing import Dict, List, Tuple
from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL_NAME, SKILL_CATEGORIES
from .utils import extract_skills, analyze_response_quality
from .skill_mapper import map_skills_to_category

class ResponseAnalyzer:
    def __init__(self):
        import httpx
        self.client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            timeout=httpx.Timeout(15.0, connect=5.0)
        )

    def _fallback_analysis(self, response: str) -> Dict:
        """Fallback analysis when AI analysis fails"""
        from .utils import extract_skills
        
        skills = extract_skills(response)
        
        # Simple skill categorization
        skill_counts = {cat: 0 for cat in SKILL_CATEGORIES}
        
        for skill in skills:
            s = skill.lower()
            for cat, keywords in SKILL_CATEGORIES.items():
                for k in keywords:
                    if k.lower() in s:
                        skill_counts[cat] += 1
        
        # Determine primary skill
        primary_skill = max(skill_counts, key=skill_counts.get) if skill_counts else "backend"
        if skill_counts.get(primary_skill, 0) == 0:
            primary_skill = "backend"
        
        # Estimate experience level based on word count and content
        word_count = len(response.split())
        if word_count < 100:
            experience = "junior"
            confidence = "low"
        elif word_count < 250:
            experience = "mid"
            confidence = "medium"
        else:
            experience = "senior"
            confidence = "high"
        
        # Count projects mentioned (simple heuristic)
        project_indicators = ["project", "built", "developed", "created", "implemented", "designed"]
        projects_mentioned = sum(1 for indicator in project_indicators if indicator in response.lower())
        
        # Estimate communication quality
        if word_count < 50:
            communication = "weak"
        elif word_count > 500:
            communication = "weak"  # Too verbose
        else:
            communication = "adequate"
        
        # Calculate intro score
        intro_score = 6  # Base
        if len(skills) >= 3:
            intro_score += 1
        if projects_mentioned >= 2:
            intro_score += 1
        if word_count >= 150 and word_count <= 400:
            intro_score += 1
        if communication == "adequate":
            intro_score += 1
        
        return {
            "skills": skills,
            "experience": experience,
            "primary_skill": primary_skill,
            "confidence": confidence,
            "communication": communication,
            "projects_mentioned": projects_mentioned,
            "word_count": word_count,
            "intro_score": min(10, max(1, intro_score))  # Keep between 1-10
        }



    def _parse_intro_analysis(self, analysis_text: str, original_response: str) -> Dict:
        """Parse introduction analysis with detailed metrics"""
        # Initialize with defaults
        result = {
            "skills": [],
            "experience": "mid",
            "primary_skill": "frontend",
            "confidence": "medium",
            "communication": "adequate",
            "projects_mentioned": 0,
            "word_count": len(original_response.split()),
            "intro_score": 7
        }
        
        # If analysis_text is empty or too short, use fallback
        if not analysis_text or len(analysis_text.strip()) < 20:
            print("AI analysis text too short, using enhanced fallback")
            return self._enhanced_fallback_analysis(original_response)
        
        lines = analysis_text.strip().split('\n')
        
        # Try to extract information with multiple patterns
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            line_lower = line.lower()
            
            # Extract skills with multiple patterns
            if "skill" in line_lower and ("primary" in line_lower or "main" in line_lower or ":" in line):
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        skill_text = parts[1].strip()
                        # Extract skill from text
                        skill = self._extract_skill_from_text(skill_text)
                        if skill:
                            result["primary_skill"] = skill
            
            # Extract experience level
            elif "experience" in line_lower and ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    exp_text = parts[1].strip().lower()
                    result["experience"] = self._categorize_experience(exp_text)
            
            # Extract confidence
            elif "confidence" in line_lower and ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    conf_text = parts[1].strip().lower()
                    result["confidence"] = self._categorize_confidence(conf_text)
            
            # Extract communication
            elif "communication" in line_lower and ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    comm_text = parts[1].strip().lower()
                    result["communication"] = self._categorize_communication(comm_text)
            
            # Extract projects count
            elif "project" in line_lower and ":" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    try:
                        result["projects_mentioned"] = int(parts[1].strip())
                    except:
                        # Try to extract number from text
                        numbers = re.findall(r'\d+', parts[1])
                        if numbers:
                            result["projects_mentioned"] = int(numbers[0])
            
            # Extract all skills mentioned (not just primary)
            elif "skill" in line_lower and ":" in line and "primary" not in line_lower and "main" not in line_lower:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    skills_text = parts[1].strip()
                    # Parse comma-separated skills
                    skills = [s.strip().lower() for s in skills_text.split(",") if s.strip()]
                    if skills:
                        result["skills"] = skills
        
        # If no skills extracted, use fallback extraction
        if not result["skills"]:
            result["skills"] = extract_skills(original_response)
        
        # Calculate a more nuanced score based on the actual response content
        result["intro_score"] = self._calculate_intro_score(result, original_response)
        
        # If we got generic defaults, try to infer better from the response
        if result["primary_skill"] == "frontend" and result["experience"] == "mid" and result["confidence"] == "medium":
            # Try to infer from response content
            result = self._infer_from_content(original_response, result)
        
        return result
    
    def _extract_skill_from_text(self, text: str) -> str:
        """Extract skill category from text using config first"""
        if not text:
            return "general"
            
        text_lower = text.lower().strip()
        # Normalize text to handle underscore/space/hyphen mismatches
        normalized_text = text_lower.replace('_', ' ').replace('-', ' ')
        
        # Use config-driven mapping first (Source of Truth)
        try:
            from .config import SKILL_CATEGORIES
            
            # 1. First check if the text matches any category key directly (normalized)
            for category in SKILL_CATEGORIES.keys():
                cat_lower = category.lower()
                cat_norm = cat_lower.replace('_', ' ').replace('-', ' ')
                
                # Direct match OR text contains the normalized category name
                if text_lower == cat_lower or cat_lower in text_lower or cat_norm in normalized_text:
                    return category

            # 2. Then check keywords
            for category, keywords in SKILL_CATEGORIES.items():
                for keyword in keywords:
                    kw_lower = keyword.lower()
                    kw_norm = kw_lower.replace('_', ' ').replace('-', ' ')
                    if kw_lower in text_lower or kw_norm in normalized_text:
                        return category
        except Exception as e:
            print(f"Error in skill extraction: {e}")
            pass
            
        # Hardcoded fallbacks if config fails
        skill_mapping = {
            "backend": ["backend", "back-end", "server", "api", "database", "python", "java", "node", "spring"],
            "frontend": ["frontend", "front-end", "react", "angular", "vue", "javascript", "ui", "ux"],
            "devops": ["devops", "aws", "docker", "kubernetes", "ci/cd"],
            "data_analysis": ["data science", "machine learning", "ml", "ai", "analytics"],
            "Steel_detailing": ["tekla", "autocad", "sds2", "steel detailing", "aisc", "cisc"],
            "CAE-MECHANICAL": ["hypermesh", "optistruct", "ls-dyna", "fea"]
        }
        
        for skill, keywords in skill_mapping.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return skill
        
        return "general"  # Default

    def _categorize_experience(self, text: str) -> str:
        """Categorize experience level from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["junior", "entry", "beginner", "early", "0-2", "1-3"]):
            return "junior"
        elif any(word in text_lower for word in ["senior", "lead", "principal", "expert", "5+", "7+", "10+"]):
            return "senior"
        else:
            return "mid"

    def _categorize_confidence(self, text: str) -> str:
        """Categorize confidence level from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["high", "strong", "very confident", "excellent"]):
            return "high"
        elif any(word in text_lower for word in ["low", "weak", "not confident", "poor"]):
            return "low"
        else:
            return "medium"

    def _categorize_communication(self, text: str) -> str:
        """Categorize communication quality from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["strong", "excellent", "good", "clear", "effective"]):
            return "strong"
        elif any(word in text_lower for word in ["weak", "poor", "unclear", "needs improvement"]):
            return "weak"
        else:
            return "adequate"

    def _calculate_intro_score(self, analysis: Dict, response: str) -> int:
        """Calculate introduction score based on multiple factors"""
        score = 7  # Base score
        
        # Factor 1: Word count (100-300 words is ideal)
        word_count = analysis["word_count"]
        if 150 <= word_count <= 350:
            score += 1
        elif word_count < 80:
            score -= 1
        elif word_count > 500:
            score -= 1
        
        # Factor 2: Skills mentioned
        skills_count = len(analysis["skills"])
        if skills_count >= 5:
            score += 1
        elif skills_count <= 2:
            score -= 1
        
        # Factor 3: Experience level (senior gets bonus)
        if analysis["experience"] == "senior":
            score += 1
        elif analysis["experience"] == "junior":
            score -= 0.5
        
        # Factor 4: Confidence
        if analysis["confidence"] == "high":
            score += 1
        elif analysis["confidence"] == "low":
            score -= 1
        
        # Factor 5: Communication
        if analysis["communication"] == "strong":
            score += 1
        elif analysis["communication"] == "weak":
            score -= 1
        
        # Factor 6: Projects mentioned
        if analysis["projects_mentioned"] >= 2:
            score += 1
        elif analysis["projects_mentioned"] == 0:
            score -= 1
        
        # Factor 7: Check for specific content indicators
        response_lower = response.lower()
        if any(term in response_lower for term in ["implemented", "developed", "built", "created"]):
            score += 0.5
        if any(term in response_lower for term in ["achieved", "improved", "increased", "reduced"]):
            score += 0.5
        if "team" in response_lower or "collaborat" in response_lower:
            score += 0.5
        
        # Ensure score is between 1-10
        return max(1, min(10, int(score)))

    def _infer_from_content(self, response: str, current_result: Dict) -> Dict:
        """Infer analysis from response content when AI gives generic results"""
        response_lower = response.lower()
        
        # Infer primary skill from content
        skill_indicators = {
            "backend": ["python", "java", "spring", "django", "flask", "node", "express", "api", "server", "database"],
            "frontend": ["react", "angular", "vue", "javascript", "typescript", "html", "css", "ui", "frontend"],
            "devops": ["aws", "docker", "kubernetes", "terraform", "ci/cd", "devops", "infrastructure"],
            "data": ["machine learning", "data science", "ai", "ml", "tensorflow", "pytorch", "analytics"],
            "mobile": ["android", "ios", "mobile", "react native", "flutter", "swift", "kotlin"]
        }
        
        skill_scores = {skill: 0 for skill in skill_indicators.keys()}
        for skill, indicators in skill_indicators.items():
            for indicator in indicators:
                if indicator in response_lower:
                    skill_scores[skill] += 1
        
        # Update primary skill if we found strong indicators
        max_skill = max(skill_scores, key=skill_scores.get) 
        if skill_scores[max_skill] > 2:  # Only update if we have strong evidence
            current_result["primary_skill"] = max_skill
        
        # Infer experience from content
        word_count = len(response.split())
        senior_indicators = ["led", "managed", "architected", "designed", "mentored", "10+", "8+", "senior"]
        junior_indicators = ["recent graduate", "bootcamp", "entry level", "seeking first", "0-2 years", "1-3 years"]
        
        senior_count = sum(1 for indicator in senior_indicators if indicator in response_lower)
        junior_count = sum(1 for indicator in junior_indicators if indicator in response_lower)
        
        if senior_count > 2:
            current_result["experience"] = "senior"
            current_result["confidence"] = "high"
        elif junior_count > 1:
            current_result["experience"] = "junior"
            current_result["confidence"] = "medium"
        elif word_count > 300:
            current_result["experience"] = "senior"
            current_result["confidence"] = "high"
        elif word_count < 100:
            current_result["experience"] = "junior"
            current_result["confidence"] = "medium"
        
        # Infer confidence from sentence structure and assertiveness
        confident_indicators = ["confident", "experienced", "expert", "proficient", "strong", "extensive"]
        uncertain_indicators = ["basic", "familiar", "learning", "beginner", "some experience"]
        
        confident_count = sum(1 for indicator in confident_indicators if indicator in response_lower)
        uncertain_count = sum(1 for indicator in uncertain_indicators if indicator in response_lower)
        
        if confident_count > uncertain_count:
            current_result["confidence"] = "high"
        elif uncertain_count > confident_count:
            current_result["confidence"] = "low"
        
        return current_result

    def _enhanced_fallback_analysis(self, response: str) -> Dict:
        """Enhanced fallback analysis with better inference"""
        from .utils import extract_skills
        
        skills = extract_skills(response)
        word_count = len(response.split())
        
        # Skill inference uses SKILL_CATEGORIES from config
        
        skill_scores = {skill: 0 for skill in SKILL_CATEGORIES.keys()}
        for skill in skills:
            skill_lower = skill.lower()
            for skill_type, indicators in SKILL_CATEGORIES.items():
                if any(indicator.lower() in skill_lower for indicator in indicators):
                    skill_scores[skill_type] += 1
        
        # If still no matches, try keyword matching on full text
        if max(skill_scores.values()) == 0:
            for skill_type, indicators in SKILL_CATEGORIES.items():
                for indicator in indicators:
                    if indicator.lower() in response.lower():
                        skill_scores[skill_type] += 1

        primary_skill = max(skill_scores, key=skill_scores.get) # type: ignore
        if skill_scores[primary_skill] == 0:
            primary_skill = "general"
        
        # Enhanced experience inference
        senior_keywords = ["led", "managed", "architected", "designed", "mentored", "10+", "6+", "7+", "8+", "9+", "senior", "principal", "lead"]
        junior_keywords = ["recent graduate", "bootcamp", "entry level", "seeking first","0-2 years", "1-3 years", "3 years", "months", "1 years", "2 years", "junior"]
        
        senior_count = sum(1 for keyword in senior_keywords if keyword in response.lower())
        junior_count = sum(1 for keyword in junior_keywords if keyword in response.lower())
        
        if senior_count > 2:
            experience = "senior"
            confidence = "high"
        elif junior_count > 1:
            experience = "junior"
            confidence = "medium"
        elif word_count > 400:
            experience = "senior"
            confidence = "high"
        elif word_count < 150:
            experience = "junior"
            confidence = "medium"
        else:
            experience = "mid"
            confidence = "medium"
        
        # Enhanced project counting
        project_patterns = [
            r"project\s+(?:called|named|titled)?\s*['\"]?([^'\"]+)['\"]?",
            r"built\s+(?:a|an)?\s*([^,.]+)",
            r"developed\s+(?:a|an)?\s*([^,.]+)",
            r"created\s+(?:a|an)?\s*([^,.]+)"
        ]
        
        projects_mentioned = 0
        for pattern in project_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            projects_mentioned += len(matches)
        
        # Enhanced communication assessment
        sentence_count = len([s for s in response.split('.') if s.strip()])
        avg_sentence_length = word_count / max(1, sentence_count)
        
        if avg_sentence_length > 25 or word_count > 500:
            communication = "weak"  # Too verbose
        elif avg_sentence_length < 10 or word_count < 80:
            communication = "weak"  # Too brief
        else:
            communication = "adequate"
        
        # Calculate score
        intro_score = 6
        if len(skills) >= 4:
            intro_score += 1
        if projects_mentioned >= 2:
            intro_score += 1
        if 150 <= word_count <= 400:
            intro_score += 1
        if confidence == "high":
            intro_score += 1
        if communication == "adequate":
            intro_score += 1
        
        return {
            "skills": skills,
            "experience": experience,
            "primary_skill": primary_skill,
            "confidence": confidence,
            "communication": communication,
            "projects_mentioned": projects_mentioned,
            "word_count": word_count,
            "intro_score": min(10, max(1, intro_score))
        }

    def evaluate_answer(self, question: str, answer: str, question_type: str = "technical") -> Dict:
        """Evaluate candidate's answer quality with detailed scoring"""
        
        # First, get basic metrics
        word_count = len(answer.split())
        metrics = analyze_response_quality(answer)
        
        if question_type == "behavioral":
            prompt = f"""
            Evaluate this behavioral interview answer using behavioral competency metrics.
            
            Question: {question}
            Answer: {answer}
            
            Score on a scale of 0-10 for each behavioral competency:
            1. Relevance (0-10): How well does the answer address the specific situation and question asked?
            2. Action & Impact (0-10): Does the candidate describe clear actions they took and the resulting outcomes?
            3. Clarity (0-10): Is the answer clearly articulated, structured (e.g., STAR method), and easy to follow?
            
            Also consider:
            - **CRITICAL CHECKS**: Did the candidate simply copy-paste or repeat the question as their answer, provide a nonsensical/irrelevant/silly response, or exhibit inappropriate behavior? If yes, severely penalize the scores (set to 0) and explicitly state this major red flag in the Weaknesses.
            - Word count: {word_count} (ideal: 50-200 words)
            - Use of specific, real-world examples?

            Provide the evaluation scores in this exact JSON structure and nothing else:
            {{
                "Relevance": [score],
                "Action & Impact": [score],
                "Clarity": [score],
                "Overall": [average score],
                "Strengths": ["key strength 1", "key strength 2"],
                "Weaknesses": ["area for improvement 1"]
            }}
            """
            system_msg = "You are an HR recruiter evaluating behavioral answers using behavioral competency frameworks. Be fair but critical."
            
            try:
                evaluation = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=350
                )
                eval_text = evaluation.choices[0].message.content  # type: ignore
                
                try:
                    import json as _json
                    cleaned = eval_text.replace("```json", "").replace("```", "").strip()
                    parsed = _json.loads(cleaned)
                    
                    res = {
                        "relevance": float(parsed.get("Relevance", parsed.get("relevance", 0))),
                        "action_impact": float(parsed.get("Action & Impact", parsed.get("action_impact", 0))),
                        "clarity": float(parsed.get("Clarity", parsed.get("clarity", 0))),
                        "overall": float(parsed.get("Overall", parsed.get("overall", 0))),
                        "strengths": parsed.get("Strengths", parsed.get("strengths", [])),
                        "weaknesses": parsed.get("Weaknesses", parsed.get("weaknesses", []))
                    }
                    if res["overall"] > 0:
                        return res
                except Exception:
                    pass
                
                return self._parse_behavioral_evaluation(eval_text, word_count)
            except Exception as e:
                print(f"AI behavioral evaluation error: {e}")
                return self._fallback_behavioral_evaluation(word_count)

        elif question_type == "aptitude":
            prompt = f"""
            Evaluate this aptitude interview answer for correctness.
            Aptitude questions often have a specific correct answer, but candidates might format it differently (e.g., "50", "50 hours", "fifty", "50 hrs").
            
            Question: {question}
            Candidate's Answer: {answer}
            
            Determine if the candidate's answer is logically equivalent to the correct answer. 
            Do not penalize for spelling errors, different units (if contextually obvious), or extra conversational text (e.g., "I think the answer is 50").
            If it is completely wrong or nonsensical, it is incorrect.
            
            Provide the result in this exact format:
            Correctness: [10 if correct, 0 if incorrect]
            Overall: [same as Correctness]
            Strengths: [Brief reason why it's correct or incorrect]
            Weaknesses: [None]
            """
            system_msg = "You are an evaluator checking aptitude test answers for logical equivalence to the correct answer."
            
            try:
                evaluation = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=150
                )
                eval_text = evaluation.choices[0].message.content  # type: ignore
                # Reuse the parsed detailed evaluation since it just finds numbers and lists
                return self._parse_detailed_evaluation(eval_text, word_count, metrics)
            except Exception as e:
                print(f"AI aptitude evaluation error: {e}")
                # Fallback to incorrect if AI fails
                return {"overall": 0, "technical_accuracy": 0, "completeness": 0, "clarity": 0, "depth": 0, "practicality": 0}

        else:
            prompt = f"""
            Evaluate this technical interview answer:
            
            Question: {question}
            Answer: {answer}
            
            Score on a scale of 1-10 for each category:
            1. Technical Accuracy (0-10): How correct is the technical information?
            2. Completeness (0-10): Does it fully address the question?
            3. Clarity (0-10): Is it well-structured and easy to understand?
            4. Depth (0-10): Does it show deep understanding or just surface-level?
            5. Practicality (0-10): Does it include real-world examples or applications?
            
            Also consider:
            - **CRITICAL CHECKS**: Did the candidate simply copy-paste the question as their answer, provide a nonsensical/irrelevant/silly response, or exhibit inappropriate behavior? If yes, severely penalize the scores (upto 1) and explicitly state this major red flag in the Weaknesses.
            - Word count: {word_count} (ideal: 80-200 words)
            - Technical terms used appropriately?
            - Examples provided?
            - Structure and organization?
            
            Provide the evaluation scores in this exact JSON structure and nothing else:
            {{
                "Technical Accuracy": [score],
                "Completeness": [score],
                "Clarity": [score],
                "Depth": [score],
                "Practicality": [score],
                "Overall": [average score],
                "Strengths": ["key strength 1", "key strength 2"],
                "Weaknesses": ["area for improvement 1"]
            }}
            """
            system_msg = "You are a technical recruiter. Return valid JSON only, following the exact structure without markdown enclosing blocks."
        
        try:
            evaluation = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3, # slightly lower temperature for more absolute score indexing triggers
                max_tokens=350
            )
            
            eval_text = evaluation.choices[0].message.content # type: ignore
            
            # JSON Fallback extractor integration Node triggers
            try:
                import json as _json
                cleaned = eval_text.replace("```json", "").replace("```", "").strip()
                parsed = _json.loads(cleaned)
                
                res = {
                    "technical_accuracy": float(parsed.get("Technical Accuracy", parsed.get("technical_accuracy", 0))),
                    "completeness": float(parsed.get("Completeness", parsed.get("completeness", 0))),
                    "clarity": float(parsed.get("Clarity", parsed.get("clarity", 0))),
                    "depth": float(parsed.get("Depth", parsed.get("depth", 0))),
                    "practicality": float(parsed.get("Practicality", parsed.get("practicality", 0))),
                    "overall": float(parsed.get("Overall", parsed.get("overall", 0))),
                    "strengths": parsed.get("Strengths", parsed.get("strengths", [])),
                    "weaknesses": parsed.get("Weaknesses", parsed.get("weaknesses", []))
                }
                if res["overall"] > 0:
                     return res
            except Exception:
                pass # Continue to standard line splits fallback Node triggers
                
            return self._parse_detailed_evaluation(eval_text, word_count, metrics)
            
        except Exception as e:
            print(f"AI evaluation error: {e}")
            # Fallback to rule-based scoring
            return self._fallback_evaluation(question, answer, word_count, metrics)

    @staticmethod
    def _parse_score(text: str) -> float:
        """Extract the first numeric value (int or float) from a string.
        Handles cases like '1 (very low)', '1/10', '1.5 — poor', etc."""
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', text.strip())
        if match:
            return float(match.group(1))
        raise ValueError(f"No numeric score found in: {text!r}")

    def _parse_detailed_evaluation(self, eval_text: str, word_count: int, metrics: Dict) -> Dict:
        """Parse detailed AI evaluation"""
        scores = {
            "technical_accuracy": 0,
            "completeness": 0,
            "clarity": 0,
            "depth": 0,
            "practicality": 0,
            "overall": 0,
            "strengths": [],
            "weaknesses": []
        }
        
        lines = eval_text.strip().split('\n')
        strengths_found = False
        weaknesses_found = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Parse scores
            if "technical accuracy:" in line_lower:
                try:
                    scores["technical_accuracy"] = self._parse_score(line.split(":", 1)[1])
                except:
                    pass
            elif "completeness:" in line_lower:
                try:
                    scores["completeness"] = self._parse_score(line.split(":", 1)[1])
                except:
                    pass
            elif "clarity:" in line_lower:
                try:
                    scores["clarity"] = self._parse_score(line.split(":", 1)[1])
                except:
                    pass
            elif "depth:" in line_lower:
                try:
                    scores["depth"] = self._parse_score(line.split(":", 1)[1])
                except:
                    pass
            elif "practicality:" in line_lower:
                try:
                    scores["practicality"] = self._parse_score(line.split(":", 1)[1])
                except:
                    pass
            elif "overall:" in line_lower:
                try:
                    scores["overall"] = self._parse_score(line.split(":", 1)[1])
                except:
                    pass
            
            # Parse strengths and weaknesses
            elif "strengths:" in line_lower:
                strengths_found = True
                weaknesses_found = False
                strength_text = line.split(":", 1)[1].strip()
                if strength_text:
                    scores["strengths"].append(strength_text)
            elif "weaknesses:" in line_lower:
                strengths_found = False
                weaknesses_found = True
                weakness_text = line.split(":", 1)[1].strip()
                if weakness_text:
                    scores["weaknesses"].append(weakness_text)
            elif strengths_found and line_lower and not line_lower.startswith(("technical", "completeness", "clarity", "depth", "practicality", "overall", "weaknesses")):
                scores["strengths"].append(line.strip())
            elif weaknesses_found and line_lower and not line_lower.startswith(("technical", "completeness", "clarity", "depth", "practicality", "overall", "strengths")):
                scores["weaknesses"].append(line.strip())
        
        # Adjust based on word count (80-200 words ideal for technical answers)
        if 80 <= word_count <= 200:
            scores["completeness"] = min(10, scores["completeness"] + 1)
            scores["overall"] = min(10, (sum([scores["technical_accuracy"], scores["completeness"], 
                                            scores["clarity"], scores["depth"], scores["practicality"]]) / 5))
        elif word_count < 50:
            scores["completeness"] = max(0, scores["completeness"] - 2)
            scores["overall"] = max(0, scores["overall"] - 1)
        elif word_count > 300:
            scores["clarity"] = max(0, scores["clarity"] - 1)
        
        # Adjust based on metrics
        if metrics["has_examples"]:
            scores["practicality"] = min(10, scores["practicality"] + 1)
        
        if metrics["has_technical_terms"]:
            scores["technical_accuracy"] = min(10, scores["technical_accuracy"] + 0.5)
        
        # Ensure overall is average of categories
        category_scores = [scores["technical_accuracy"], scores["completeness"], 
                            scores["clarity"], scores["depth"], scores["practicality"]]
        scores["overall"] = sum(category_scores) / len(category_scores)
        
        # Raise error if everything is 0 to trigger overall fallback safety layouts
        if scores["overall"] == 0:
            raise ValueError("Parsed score is 0.0 across categories, likely parsing failed setup")

        # Round scores
        for key in scores:
            if isinstance(scores[key], (int, float)):
                scores[key] = round(scores[key], 1)
        return scores

    def _parse_behavioral_evaluation(self, eval_text: str, word_count: int) -> Dict:
        """Parse behavioral AI evaluation with competency metrics"""
        scores = {
            "relevance": 0.0,
            "action_impact": 0.0,
            "clarity": 0.0,
            "overall": 0.0,
            "strengths": [],
            "weaknesses": []
        }
        
        lines = eval_text.strip().split('\n')
        strengths_found = False
        weaknesses_found = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Parse scores
            if "relevance:" in line_lower:
                try: scores["relevance"] = self._parse_score(line.split(":", 1)[1])
                except: pass
            elif "action" in line_lower and "impact" in line_lower:
                try: scores["action_impact"] = self._parse_score(line.split(":", 1)[1])
                except: pass
            elif "clarity:" in line_lower:
                try: scores["clarity"] = self._parse_score(line.split(":", 1)[1])
                except: pass
            elif "overall:" in line_lower:
                try: scores["overall"] = self._parse_score(line.split(":", 1)[1])
                except: pass
            
            # Parse strengths and weaknesses
            elif "strengths:" in line_lower:
                strengths_found = True
                weaknesses_found = False
                strength_text = line.split(":", 1)[1].strip()
                if strength_text:
                    scores["strengths"].append(strength_text)
            elif "weaknesses:" in line_lower:
                strengths_found = False
                weaknesses_found = True
                weakness_text = line.split(":", 1)[1].strip()
                if weakness_text:
                    scores["weaknesses"].append(weakness_text)
            elif strengths_found and line_lower and not line_lower.startswith(("communication", "coherence", "empathy", "situational", "self", "overall", "weaknesses")):
                scores["strengths"].append(line.strip())
            elif weaknesses_found and line_lower and not line_lower.startswith(("communication", "coherence", "empathy", "situational", "self", "overall", "strengths")):
                scores["weaknesses"].append(line.strip())
        
        # Word count adjustments
        if word_count < 50:
            scores["clarity"] = max(0, scores["clarity"] - 2)
            scores["overall"] = max(0, scores["overall"] - 1)
        elif 80 <= word_count <= 250:
            pass # Keep AI scores intact
        
        category_scores = [scores["relevance"], scores["action_impact"], scores["clarity"]]
        scores["overall"] = sum(category_scores) / len(category_scores)
        
        for key in scores:
            if isinstance(scores[key], (int, float)):
                scores[key] = round(scores[key], 1)
        
        return scores

    def _fallback_evaluation(self, question: str, answer: str, word_count: int, metrics: Dict) -> Dict:
        """Fallback evaluation when AI fails"""
        base_score = 5
        
        # Adjust based on word count
        if 100 <= word_count <= 250:
            base_score = 7
        elif 50 <= word_count < 100:
            base_score = 6
        elif word_count < 50:
            base_score = 4
        elif word_count > 300:
            base_score = 6  # Might be too verbose
        
        # Adjust based on metrics
        if metrics["has_examples"]:
            base_score += 1
        if metrics["has_technical_terms"]:
            base_score += 1
        if metrics["has_explanation"]:
            base_score += 1
        
        # Check for question-specific indicators
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        if "debug" in question_lower and any(term in answer_lower for term in ["log", "monitor", "analyze", "profile"]):
            base_score += 1
        
        if "design" in question_lower and any(term in answer_lower for term in ["scalable", "architecture", "components", "trade-off"]):
            base_score += 1
        
        if "difference between" in question_lower and any(term in answer_lower for term in ["vs", "versus", "while", "whereas", "on the other hand"]):
            base_score += 1
        
        # Cap score
        final_score = max(1, min(10, base_score))
        
        # Generate simple strengths/weaknesses
        strengths = []
        weaknesses = []
        
        if word_count >= 100:
            strengths.append("Provides detailed explanations")
        else:
            weaknesses.append("Could provide more detail")
        
        if metrics["has_examples"]:
            strengths.append("Uses practical examples")
        else:
            weaknesses.append("Lacks concrete examples")
        
        return {
            "technical_accuracy": final_score,
            "completeness": final_score,
            "clarity": final_score,
            "depth": final_score,
            "practicality": final_score,
            "overall": final_score,
            "strengths": strengths[:2],
            "weaknesses": weaknesses[:2]
        }

    def _fallback_behavioral_evaluation(self, word_count: int) -> Dict:
        """Fallback evaluation for behavioral questions when AI fails"""
        base_score = 5
        if 80 <= word_count <= 250:
            base_score = 7
        if word_count < 50:
            base_score = 0  # Severe penalty for extremely short or repeated question
            
        return {
            "relevance": base_score,
            "action_impact": base_score,
            "clarity": base_score,
            "overall": base_score,
            "strengths": ["Answered the question"] if word_count >= 50 else [],
            "weaknesses": ["Could provide more detail"] if word_count < 100 else []
        }

    def check_for_termination(self, response: str, question_type: str = "technical") -> Tuple[bool, str]:
        """Check if interview should be terminated"""
        from .config import ABUSIVE_KEYWORDS, TERMINATION_KEYWORDS
        
        if not response or response.isspace():
            return False, ""
        
        response_lower = response.lower().strip()
        
        # Check for abusive language
        for keyword in ABUSIVE_KEYWORDS:
            if keyword in response_lower:
                return True, "misconduct"
        
        # Check for explicit termination request
        # Use regex to match whole words only to avoid false positives (e.g., "backend" matching "end")
        for keyword in TERMINATION_KEYWORDS:
            if re.search(r'\b' + re.escape(keyword) + r'\b', response_lower):
                return True, "candidate_request"
        
        # Check for extremely poor responses
        # SKIP THIS for aptitude stage — short answers (e.g., "42", "Paris") are common and valid.
        # DISABLED: Too aggressive for single short responses. AI will handle scoring.
        # if question_type != "aptitude" and len(response.split()) < 5 and "skip" not in response_lower:
        #     return True, "poor_response"
        
        return False, ""
    
    def analyze_introduction(self, response: str, job_title: str = "") -> Dict:
        """Analyze candidate's introduction with better AI analysis and job context"""
        from .config import SKILL_CATEGORIES
        categories = list(SKILL_CATEGORIES.keys())
        
        job_context = f"This is for the position of '{job_title}'." if job_title else ""
        
        prompt = f"""
            Analyze the candidate's introduction as a technical recruiter.
            {job_context}
            
            Candidate Data/Summary:
            {response[:1000]}

            Evaluation guidelines:
            - Be fair and slightly liberal in interpretation, but do NOT overestimate the
            candidate’s skills, experience, or confidence beyond what is clearly stated.
            - Base all judgments strictly on the content provided.
            - Assume a junior-to-mid level candidate unless strong evidence suggests otherwise.
            - Avoid generic assumptions or exaggerated classifications.

            Provide the analysis in EXACTLY the following format:

            Skills: [comma-separated list of specific technical skills explicitly mentioned or strongly implied]
            Experience Level: [junior/mid/senior]
            Primary Technical Area: [{"/".join(categories)}]
            Confidence: [low/medium/high]
            Communication: [weak/adequate/strong]
            Projects Mentioned: [number]
        """
        
        try:
            print("[DEBUG] Sending to AI for analysis...")
            response_analysis = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": '''
                            You are a technical recruiter evaluating candidate responses during an interview. Analyze each answer carefully and provide specific, detailed, and objective feedback based strictly on the content provided.
                            Evaluate the candidate liberally and fairly, recognizing effort, clarity, and correct reasoning, but do not inflate scores or assessments beyond what the response genuinely demonstrates.
                            The interview difficulty level should be considered medium, so expectations should align with a competent junior-to-mid-level candidate rather than an expert.
                            Focus your evaluation on:
                            Technical correctness and conceptual understanding
                            Clarity of explanation and communication
                            Practical thinking and real-world relevance
                            Completeness of the response relative to the question
                            Be balanced in your judgment: acknowledge strengths clearly, point out gaps constructively, and avoid overly harsh or overly generous evaluations. The goal is to provide a realistic assessment of the candidate’s readiness at a medium-level technical interview. 
                    '''},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Slightly higher temperature for more varied responses
                max_tokens=250
            )
            
            analysis_text = response_analysis.choices[0].message.content # type: ignore
            # (f"[DEBUG] AI Response:\n{analysis_text}")
            
            return self._parse_intro_analysis(analysis_text, response)
        except Exception as e:
            print(f"[DEBUG] AI analysis error: {e}")
            return self._enhanced_fallback_analysis(response)
        
    