from openai import OpenAI
import random
from typing import List, Dict
from .config import SKILL_CATEGORIES, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL_NAME

class QuestionGenerator:
    def _get_varied_fallbacks(self, category: str, difficulty: str, needed: int, exclude: List[str] = None) -> List[str]:
        """Generate a variety of fallback questions to avoid repetition."""
        if exclude is None:
            exclude = []
            
        if "scenario" in difficulty or "deep" in difficulty:
            templates = [
                f"Can you describe a real-world scenario where you applied your knowledge of {category}?",
                f"Walk me through a complex problem you solved using {category}.",
                f"What is the most challenging project you've handled involving {category}?",
                f"How would you approach a critical failure or bottleneck in a {category} system?",
                f"Describe a time you had to optimize the performance of a {category} implementation."
            ]
        else:
            templates = [
                f"Can you explain a fundamental concept related to {category}?",
                f"What are the core principles or best practices when working with {category}?",
                f"How do you handle common issues or errors in {category}?",
                f"Explain the role and importance of {category} in a modern development stack.",
                f"What are the key advantages and disadvantages of using {category}?"
            ]
            
        # Filter out already present questions
        available = [t for t in templates if t not in exclude]
        if not available:
            available = templates # Restart if all excluded
            
        result = []
        import random
        random.shuffle(available)
        
        while len(result) < needed:
            result.append(available[len(result) % len(available)])
            
        return result

    def __init__(self):
        if OPENROUTER_API_KEY:
            self.client = OpenAI(
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                timeout=10.0
            )
        else:
            self.client = None
            print("QuestionGenerator: AI Client disabled (Missing API Key)")

    # 1️⃣ FIRST QUESTION (GENERIC)
    def generate_general_intro_question(self) -> str:
        return (
            "Please describe your professional background, key skills, tools you use, "
            "and the type of projects you have worked on."
        )

    # 2️⃣ TECHNICAL QUESTIONS (CATEGORY LOCKED)
    def generate_initial_skill_questions(
        self, skill_category: str, candidate_level: str = "mid"
    ) -> List[str]:

        skills = SKILL_CATEGORIES.get(skill_category, [])
        skills_text = ", ".join(skills[:6]) if skills else skill_category

        prompt = f"""
        You are an interviewer.

        Candidate level: {candidate_level}
        Domain: {skill_category}
        Key skills: {skills_text}

        Generate:
        - 2 fundamental questions
        - 2 practical questions
        - 1 scenario-based question

        Each must be strictly related to the domain.
        
        IMPORTANT: Vary the questions. Do not use the same standard questions every time.
        Focus on: {random.choice(['performance and optimization', 'security and best practices', 'architecture and design', 'debugging and troubleshooting', 'modern features and updates'])}
        """

        try:
            res = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9, # Increased for variance
                max_tokens=250
            )

            import re
            # Clean up leading numbers (1. Question -> Question)
            cleaned_questions = []
            content = res.choices[0].message.content
            if content:
                for q in [x for x in content.split("\n") if x.strip().endswith("?")]:
                    cleaned = re.sub(r'^\d+[\.\)]\s*', '', q.strip())
                    cleaned_questions.append(cleaned)
            
            return cleaned_questions  # Return all generated questions

        except Exception:
            return self._fallback(skill_category)

    def generate_behavioral_question_ai(
        self,
        candidate_background: dict,
        context: list | None = None
    ) -> str:
        """
        Generate a behavioral question based on candidate background.
        Context is optional and used for future adaptive behavior.
        """

        domain = candidate_background.get("primary_skill", "general")

        if domain == "bim":
            return (
                "Tell me about a time you identified a coordination or clash issue "
                "that was outside your assigned scope in a BIM project. "
                "How did you handle it and what was the outcome?"
            )

        return (
            "Tell me about a time when you faced an unexpected challenge at work. "
            "How did you take ownership of the situation and resolve it?"
        )


    def _fallback(self, category: str) -> List[str]:
        skills = SKILL_CATEGORIES.get(category, [])
        if not skills:
            return [
                "Explain a core concept in your domain?",
                "Describe a real-world problem you solved?",
                "How do you stay updated in your field?"
            ]

        return [
            f"Explain a core concept in {skills[0]}?",
            f"How do you use {skills[1] if len(skills) > 1 else skills[0]}?",
            f"What challenges do you face with {skills[-1]}?"
        ]

    # ── METHODS FROM IMPROVED VERSION ────────────────────────────────────────

    def generate_specific_questions(
        self,
        skill_category: str,
        count: int,
        difficulty: str = "basic",
        extracted_skills_list: List[str] = None
    ) -> List[str]:
        """
        Generate specific number of questions for a skill and difficulty.
        Difficulty: 'basic' or 'scenario-based/deep'
        """
        if not self.client:
            return [f"Tell me about your {difficulty} experience with {skill_category}."] * count

        # If actual skills from the resume are provided, prioritize them.
        # Otherwise, fall back to the generic category skills.
        if extracted_skills_list:
            skills_text = f"Candidate's exact matching skills: {', '.join(extracted_skills_list)}"
        else:
            skills = SKILL_CATEGORIES.get(skill_category, [])
            skills_text = ", ".join(skills[:8]) if skills else skill_category

        if difficulty == "basic":
            prompt_difficulty = "fundamental, simple definitions, core conceptual knowledge, very basic questions. Do NOT ask scenario-based questions. Keep them short and simple."
        else:
            prompt_difficulty = "scenario-based, follow-up style, detailed implementation, 'how would you handle X', practical problem solving"

        prompt = f"""
        You are an expert technical interviewer assessing a candidate.
        Domain: {skill_category}
        {skills_text}

        Generate exactly {count} {difficulty} interview questions.
        Focus: {prompt_difficulty}

        CRITICAL INSTRUCTION: You must strictly ask questions related to the 'Candidate's exact matching skills' listed above THAT ARE HIGHLY RELEVANT to the {skill_category} domain. 
        
        DO NOT ask about generic office software (e.g., MS Office, Word, Excel).
        DO NOT ask about soft skills or leadership here.
        
        IMPORTANT: Under NO CIRCUMSTANCES should you ask about a technology (e.g. Go, Java, React) if it is NOT part of the {skill_category} domain, even if it might be in the resume. Your goal is to assess {skill_category} proficiency. Do NOT blend unrelated technologies into the questions (e.g., do NOT ask 'How to use Go in {skill_category}' if Go is a general programming language and {skill_category} is a mechanical/structural field).
        
        If no relevant specific technologies are found in the skills list, ask about standard architectural concepts, industry best practices, or fundamentals of {skill_category}.

        Return valid JSON array of strings, e.g. ["Question 1", "Question 2"]
        """

        try:
            import json
            import re

            res = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=600
            )

            content = res.choices[0].message.content
            content = re.sub(r"```json", "", content)
            content = re.sub(r"```", "", content).strip()

            try:
                questions = json.loads(content)
                if isinstance(questions, list):
                    # Filter out empty or non-string results
                    questions = [str(q).strip() for q in questions if q and str(q).strip()]
                    
                    if len(questions) < count:
                        fallbacks = self._get_varied_fallbacks(skill_category, difficulty, count - len(questions), exclude=questions)
                        questions.extend(fallbacks)
                        
                    return questions[:count]
            except:
                pass

            # Fallback regex splitting if JSON fails
            questions = []
            for line in content.split('\n'):
                line = line.strip()
                if '?' in line:
                    clean = re.sub(r'^\d+[\.\\)]\s*', '', line)
                    if clean:
                        questions.append(clean)

            if len(questions) < count:
                fallbacks = self._get_varied_fallbacks(skill_category, difficulty, count - len(questions), exclude=questions)
                questions.extend(fallbacks)
                
            return questions[:count]

        except Exception as e:
            print(f"Error generating {difficulty} questions: {e}")
            return [f"Describe a {difficulty} concept in {skill_category}."] * count

    def generate_behavioral_questions_batch(self, count: int, behavioral_role: str = "general") -> List[str]:
        """Generate a batch of behavioral questions based on role level"""
        if not self.client:
            return ["Tell me about a time you worked in a team."] * count

        role_focus = ""
        if behavioral_role == "junior":
            role_focus = "Focus on: Learning, Adaptability, Following instructions, Teamwork, and Proactive communication."
        elif behavioral_role == "mid":
            role_focus = "Focus on: Ownership, Conflict Resolution, Independent Problem Solving, Mentoring juniors, and Cross-functional collaboration."
        elif behavioral_role == "lead":
            role_focus = "Focus on: Leadership, System Design Trade-offs, Project Management, Stakeholder Management, Driving team culture, and Handling critical failures."
        else:
            role_focus = "Focus on: Teamwork, Adaptability, Ownership, Conflict Resolution, and Communication."

        prompt = f"""
        You are an HR manager. Generate exactly {count} behavioral interview questions for a {behavioral_role} candidate.
        {role_focus}

        Return valid JSON array of strings.
        """

        try:
            import json
            import re

            res = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=600
            )

            content = res.choices[0].message.content
            content = re.sub(r"```json", "", content)
            content = re.sub(r"```", "", content).strip()

            try:
                if content.startswith("["):
                    questions = json.loads(content)
                    if isinstance(questions, list):
                        while len(questions) < count:
                            questions.append(f"Can you tell me about a time you faced a relevant challenge as a {behavioral_role}?")
                        return questions[:count]
            except:
                pass

            questions = []
            for line in content.split('\n'):
                if '?' in line:
                    clean = re.sub(r'^\d+[\.\\)]\s*', '', line.strip())
                    questions.append(clean)

            while len(questions) < count:
                questions.append(f"Can you tell me about a time you faced a relevant challenge as a {behavioral_role}?")
            return questions[:count]

        except Exception:
            return [f"Tell me about a challenge you faced as a {behavioral_role}."] * count

    def generate_aptitude_questions(self, count: int) -> List[dict]:
        """Generate a batch of AI aptitude questions with MCQ options"""
        if not self.client:
             return [
                 {"question": "If a train travels 60 km/h for 2 hours, how far does it go?", "options": ["120 km", "100 km", "140 km", "80 km"], "answer": 0},
                 {"question": "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost?", "options": ["$0.10", "$0.05", "$0.15", "$0.01"], "answer": 1},
                 {"question": "What is the next number in the sequence: 2, 4, 8, 16, ...?", "options": ["32", "24", "48", "64"], "answer": 0},
                 {"question": "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?", "options": ["5 minutes", "100 minutes", "20 minutes", "50 minutes"], "answer": 0},
                 {"question": "If you have a 3-liter jug and a 5-liter jug, how do you measure exactly 4 liters?", "options": ["Fill 5L, pour into 3L, empty 3L, pour remaining 2L into 3L, fill 5L, pour into 3L until full.", "Fill 3L, pour into 5L, fill 3L, pour into 5L until full.", "Fill 5L, pour into 3L.", "None of the above"], "answer": 0}
             ][:count]
             
        prompt = f"""
        You are an assessment expert creating an aptitude test.
        Generate exactly {count} logical reasoning, basic math, or analytical aptitude questions.
        
        Each question must be an object with:
        - "question": The problem statement string.
        - "options": A list of exactly 4 plausible option strings.
        - "answer": The index (0-3) of the correct option.
        
        Return valid JSON array of objects.
        """
        
        try:
            import json
            import re

            res = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=2000
            )

            content = res.choices[0].message.content
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                content = match.group(0)

            try:
                questions = json.loads(content)
                if isinstance(questions, list):
                    return questions[:count]
            except:
                pass
            
            return self.generate_aptitude_questions(0)

        except Exception:
            return self.generate_aptitude_questions(0)
