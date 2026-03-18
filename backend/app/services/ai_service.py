from openai import AsyncOpenAI
import httpx
import json
import asyncio
from functools import partial
from app.core.config import get_settings

# Import from the refactored interview_process package
# Accessing config via the package modules which now use relative imports
try:
    from backend.interview_process.question_generator import QuestionGenerator
    from backend.interview_process.response_analyzer import ResponseAnalyzer
    from backend.interview_process.utils import extract_skills
    from backend.interview_process.config import MODEL_NAME
except ImportError:
    # Fallback for when running directly within backend directory
    from interview_process.question_generator import QuestionGenerator
    from interview_process.response_analyzer import ResponseAnalyzer
    from interview_process.utils import extract_skills
    from interview_process.config import MODEL_NAME

settings = get_settings()

# Initialize modular AI services
question_gen = QuestionGenerator()
analyzer = ResponseAnalyzer()

# Helper to run sync methods in async loop
async def run_sync(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

logger = logging.getLogger(__name__)

# Helper: Direct OpenAI/Groq Call (Async) for local functions
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=15),
    reraise=True
)
async def call_openai_direct(prompt: str, system_instr: str) -> str:
    # Try Groq first (faster and cheaper), then fall back to OpenAI
    api_key = None
    base_url = None
    
    if settings.groq_keys:
        api_key = settings.groq_keys[0]
        base_url = "https://api.groq.com/openai/v1"
        model = "llama-3.3-70b-versatile"  # Groq's best model
    elif settings.openai_keys:
        api_key = settings.openai_keys[0]
        base_url = None  # Use default OpenAI base URL
        model = "gpt-4o"
    else:
        raise Exception("No API key found. Please set GROQ_API_KEY or OPENAI_API_KEY in .env file.")
        
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=httpx.Timeout(15.0, connect=5.0)  # 15s total, 5s connect
    )
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except httpx.TimeoutException as e:
        logger.warning(f"AI API Timeout (attempting retry): {e}")
        raise e
    except Exception as e:
        logger.error(f"AI API Request Error (attempting retry): {e}")
        raise e

import re

def clean_json(text: str) -> str:
    """Clean markdown code blocks from JSON string and extract first JSON object"""
    # Remove markdown code blocks
    text = text.replace("```json", "").replace("```", "").strip()
    
    # Try to find JSON object with regex if it's not clean
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
        
    match_list = re.search(r'(\[.*\])', text, re.DOTALL)
    if match_list:
        return match_list.group(1)

    return text

# ============================================================================
# Business Logic Functions
# ============================================================================

def calculate_match_percentage(extracted_skills: list, required_skills_str: str) -> float:
    """Calculate match percentage between extracted and required skills"""
    if not required_skills_str:
        return 0.0
    
    # Parse required skills
    required = set()
    try:
        # Try JSON first
        if required_skills_str.strip().startswith("["):
            req_list = json.loads(required_skills_str)
            if isinstance(req_list, list):
                for s in req_list:
                    required.add(str(s).lower().strip())
    except:
        pass
        
    if not required:
        # Fallback to splitting by comma or space
        # Replace common separators with comma
        normalized = required_skills_str.replace(";", ",").replace("\n", ",")
        # If no commas, assume space separation if it looks like a list of words
        if "," not in normalized and " " in normalized:
             # Heuristic: if it's just "Java Python", split by space
             parts = normalized.split()
        else:
             parts = normalized.split(",")
             
        for p in parts:
            clean = p.strip().lower()
            if clean:
                required.add(clean)
    
    if not required:
        return 0.0
        
    extracted_norm = set(s.lower().strip() for s in extracted_skills)
    
    # Calculate overlap
    # We use a fuzzy match or simple set intersection?
    # Simple set intersection + simple aliases usually works best for strict checking
    # But let's add some basic aliasing maps if needed? For now strict lower case match.
    
    # Handle JS vs JavaScript
    aliases = {
        "js": "javascript",
        "javascript": "js",
        "golang": "go",
        "go": "golang"
    }
    
    # Expand extracted with aliases
    expanded_extracted = set(extracted_norm)
    for s in extracted_norm:
        if s in aliases:
            expanded_extracted.add(aliases[s])
            
    matches = 0
    for req in required:
        if req in expanded_extracted:
            matches += 1
        else:
            # check for substring match if req is long? No, usually bad idea.
            pass
            
    return (matches / len(required)) * 100

async def parse_resume_with_ai(resume_text: str, job_id: int, job_description: str = "") -> dict:
    """
    Parse resume using direct OpenAI call.
    """
    prompt = f"""
    Analyze this document. First, determine if it is a Resume or CV.
    
    If it is NOT a resume (e.g., it is a research paper, article, assignment, invoice, or irrelevant text), return JSON with "is_resume": false and "summary": "Document identified as [type] instead of resume.".
    
    If it IS a resume, analyze it against the provided Job Description.
    
    Job Description:
    {job_description[:2000]}

    
    Extract:
    - List of skills (technical and soft skills)
    - Years of experience (numeric)
    - Experience Level (Intern, Junior, Mid-Level, Senior, Lead / Manager) based on the analysis
    - Education (list of degrees/certifications)
    - Previous job roles (list of job titles)
    - "summary": A comprehensive professional summary (3-4 sentences).
    - "strengths": A list of 3-5 key strengths or highlights regarding the Job Description.
    - "weaknesses": A list of 3-5 potential gaps or weaknesses regarding the Job Description.
    - "score": A Resume Score from 0 to 10 (up to 1 decimal place) based on a comprehensive analysis of skills, experience, and role fit against the JD. 10 is a perfect match.
    
    Resume content: {resume_text[:4000]}
    
    Return JSON with this exact structure:
    {{
        "is_resume": true,
        "skills": ["skill1", "skill2"],
        "experience": 3,
        "experience_level": "Mid-Level",
        "education": ["degree1", "degree2"],
        "roles": ["role1", "role2"],
        "summary": "Candidate profile summary...",
        "strengths": ["Strong PHP experience", "Good leadership skills"],
        "weaknesses": ["Lacks React native experience", "Short tenure at last job"],
        "score": 8.5,
        "match_percentage": 50
    }}
    """
    
    result = {
         "is_resume": True, # Default to True to give benefit of doubt if AI fails to toggle
         "skills": [], 
         "experience": 0, 
         "experience_level": "Unknown",
         "education": [], 
         "roles": [], 
         "summary": "No summary available.",
         "score": 0, 
         "match_percentage": 0
    }
    
    try:
        # Using a consistent system instruction
        response = await call_openai_direct(prompt, "You are an expert HR resume analyzer. You provide strict scoring and detailed analysis. Return valid JSON only.")
        data = json.loads(clean_json(response))
        result = data
        
        # Format the summary to include strengths and weaknesses
        formatted_summary = data.get("summary", "")
        
        strengths = data.get("strengths", [])
        if strengths:
            formatted_summary += "\n\n**Key Highlights:**\n" + "\n".join([f"- {s}" for s in strengths])
            
        weaknesses = data.get("weaknesses", [])
        if weaknesses:
            formatted_summary += "\n\n**Potential Gaps:**\n" + "\n".join([f"- {w}" for w in weaknesses])
            
        result["summary"] = formatted_summary

    except Exception as e:
        print(f"AI Parse Error: {e}, falling back to regex.")
        # Robust Fallback
        extracted_skills = extract_skills(resume_text)
        result["skills"] = extracted_skills
        result["summary"] = resume_text[:200] + "..." if len(resume_text) > 200 else resume_text
        result["education"] = []
        result["roles"] = []
        result["experience_level"] = "Not specified"
        result["score"] = 5.0
        result["match_percentage"] = 0.0

    # Final cleanup of results
    if not result.get("skills"):
        result["skills"] = ["General Profile"]
    if not result.get("summary"):
        result["summary"] = "AI was unable to generate a summary for this resume."
    if "score" not in result or result["score"] is None or result["score"] == 0:
         result["score"] = 5.0
    if "match_percentage" not in result or result["match_percentage"] is None:
         result["match_percentage"] = 0.0
    
    return result

async def extract_job_details(job_text: str) -> dict:
    """Extract job details using direct OpenAI call."""
    prompt = f"""
    Analyze the following job description text and extract structured information.
    
    If a field is not explicitly mentioned:
    * Attempt intelligent inference only if clearly implied (e.g., matching a domain from a standard list).
    * If not determinable, leave blank.
    * Do not fabricate.
    
    Valid options for specific fields (must match exactly or leave blank):
    - Experience Level: Intern, Junior, Mid-Level, Senior, Lead / Manager
    - Department: Engineering, Software, Support, Design, Structural Engineering, Civil Engineering, Electrical Engineering, Mechanical Engineering, Automobile Engineering, HR
    - Job Type: Full-Time, Part-Time, Contract, Internship, Temporary
    - Location: Remote, Hybrid, On-Site
    
    You must format the main "description" field as plain text EXACTLY matching this structure (use standard text and simple hyphens or bullets, NO markdown hashes like ### or asterisks **):
    
    JOB OVERVIEW
    [Concise summary of role based ONLY on provided content. No invented company context. No branding language]
    
    ROLE & RESPONSIBILITIES
    - [6-10 bullet points extracted directly. Split compound responsibilities if necessary.]
    
    QUALIFICATIONS
    - [5-10 bullet points extracted directly. Education, certifications, technical requirements, experience. Do not assume degree if not mentioned. Do not assume years of experience unless specified.]
    
    PREFERRED SKILLS
    - [Extract optional/good-to-have skills]

    Strict Rules:
    - Not invent years of experience.
    - Not assume domain if not mentioned.
    - Not fabricate job type.
    - Not assume remote/on-site unless specified.
    - Preserve domain-specific terminology.
    - Extract exactly the top 5 core, technical, domain-specific skills required for the role. Not generic soft skills unless explicitly central.
    - If more than 5 exist, select the 5 most relevant.
    - If fewer than 5 exist, extract what is available without inventing.
    - All newlines inside the description string MUST be escaped as \\n. DO NOT use raw newlines inside the JSON string values.

    Job Text:
    {job_text[:8000]}
    
    Return JSON with this exact structure (all string fields except the array):
    {{
        "title": "extracted or blank",
        "experience_level": "one of the options or blank",
        "domain": "one of the options or blank",
        "job_type": "one of the options or blank",
        "location": "one of the options or blank",
        "description": "The exact full plain text string containing overview, responsibilities, qualifications, preferred skills",
        "primary_evaluated_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"]
    }}
    """
    
    try:
        response = await call_openai_direct(prompt, "You are a precise HR data extraction tool. Return valid JSON only.")
        data = json.loads(clean_json(response), strict=False)
        return {
            "title": data.get("title", ""),
            "experience_level": data.get("experience_level", ""),
            "domain": data.get("domain", ""),
            "job_type": data.get("job_type", ""),
            "location": data.get("location", ""),
            "description": data.get("description", ""),
            "primary_evaluated_skills": data.get("primary_evaluated_skills", [])
        }
    except Exception as e:
        print(f"AI Parse Error: {e}")
        return {
            "title": "",
            "experience_level": "",
            "domain": "",
            "job_type": "",
            "location": "",
            "description": job_text[:2000], # fallback
            "primary_evaluated_skills": []
        }



async def analyze_introduction(response_text: str, job_title: str = "") -> dict:
    """Delegate to ResponseAnalyzer"""
    return await run_sync(analyzer.analyze_introduction, response_text, job_title)

async def evaluate_detailed_answer(question: str, answer: str, question_type: str = "technical") -> dict:
    """Delegate to ResponseAnalyzer"""
    return await run_sync(analyzer.evaluate_answer, question, answer, question_type)

async def generate_domain_questions(skill_category: str, candidate_level: str = "mid", count: int = 5) -> list:
    """Delegate to QuestionGenerator"""
    # question_gen returns a list of strings
    return await run_sync(question_gen.generate_initial_skill_questions, skill_category, candidate_level)

async def generate_custom_domain_questions(
    skill_category: str,
    count: int,
    difficulty: str = "basic",
    extracted_skills_list: list = None,
    required_skills: str = None
) -> list:
    """
    Generate specific questions with difficulty level and candidate skill awareness.
    Enforces strict filtering: Only uses resume skills relevant to JD or Domain.
    """
    # 1. Parse JD skills
    jd_skills = []
    if required_skills and isinstance(required_skills, str):
        try:
            import json as _json
            parsed = _json.loads(required_skills)
            if isinstance(parsed, list):
                jd_skills = [s.strip().lower() for s in parsed if s.strip()]
        except Exception:
            pass

    # 2. Parse Resume skills
    resume_skills = [s.strip().lower() for s in extracted_skills_list] if extracted_skills_list else []
    
    # 3. Filter: Intersection of Resume Skills and (JD Skills OR Domain Keywords)
    from interview_process.config import SKILL_CATEGORIES
    domain_keywords = [k.lower() for k in SKILL_CATEGORIES.get(skill_category, [])]
    
    final_skills = []
    for s in resume_skills:
        # Match if specifically in JD
        is_in_jd = s in jd_skills
        # Match if it's a canonical keyword for this industry domain
        is_in_domain = any(k in s or s in k for k in domain_keywords)
        # Match if it's the category name itself
        is_category = skill_category.lower() in s or s in skill_category.lower()
        
        if is_in_jd or is_in_domain or is_category:
            final_skills.append(s)

    # 4. If the resume has NO skills relevant to this JD, we use JD skills as fallback
    # or the domain itself. We don't want to follow irrelevant resume skills.
    input_skills = list(set(final_skills)) if final_skills else None

    return await run_sync(
        question_gen.generate_specific_questions,
        skill_category,
        count,
        difficulty,
        input_skills
    )

async def generate_behavioral_batch(count: int, behavioral_role: str = "general"):
    """Generate a batch of behavioral questions using the improved batch generator."""
    return await run_sync(question_gen.generate_behavioral_questions_batch, count=count, behavioral_role=behavioral_role)

async def generate_aptitude_batch(count: int):
    """Generate a batch of aptitude questions using the QuestionGenerator."""
    return await run_sync(question_gen.generate_aptitude_questions, count=count)




async def generate_adaptive_interview_question(previous_answer: str, previous_question: str, interview_history: list, job_title: str, candidate_skills: list, current_question_number: int) -> dict:
    """
    Delegate to QuestionGenerator for behavioral, or use domain questions for technical.
    """
    background = {"primary_skill": "general"} 
    
    # 7 questions total usually
    if current_question_number >= 2: # Technical Phase
       category = "backend" 
       if candidate_skills:
           category = candidate_skills[0] # Naive pick first skill

       # Generate a batch and pick one based on index
       questions = await run_sync(question_gen.generate_initial_skill_questions, category, "mid")
       
       # Use modulo to pick a distinct question from the batch if possible, or random
       idx = (current_question_number) % len(questions)
       q_text = questions[idx] if questions else "Describe your experience."
       
       return {"question_text": q_text, "question_type": "technical"}
    else:
       # Intro/Behavioral Phase
       q_text = await run_sync(question_gen.generate_behavioral_question_ai, background)
       return {"question_text": q_text, "question_type": "behavioral"}



# Aliases for backward compatibility
evaluate_interview_answer = evaluate_detailed_answer

async def generate_behavioral_question(job_title: str, candidate_level: str) -> str:
    """Wrapper for behavioral question generation to match legacy signature"""
    # Create a dummy background since new logic requires it
    background = {
        "primary_skill": "general", 
        "full_name": "Candidate" 
    }
    return await run_sync(question_gen.generate_behavioral_question_ai, background)


async def generate_interview_report(job_title: str, all_qa_pairs: list, overall_score: float, primary_evaluated_skills: list = None, termination_reason: str = None) -> dict:
    """
    Generate Hiring Report using OpenAI directly (Legacy Logic preserved).
    """
    qa = "\\n".join([f"Q: {i['question']} A: {i['answer']}" for i in all_qa_pairs])
    skills_context = ", ".join(primary_evaluated_skills) if primary_evaluated_skills else "General technical skills"
    
    termination_context = ""
    if termination_reason:
        termination_context = f"\n    CRITICAL CONTEXT: This interview was TERMINATED EARLY due to: '{termination_reason}'. You MUST mention this termination reason explicitly in the summary and critically factor it into your overall recommendation.\n"

    prompt = f"""
    Generate Hiring Report for {job_title}.
    {termination_context}
    You must explicitly evaluate the candidate's transcript specifically against these core skills: {skills_context}.
    For each skill:
    - Assess conceptual clarity, technical correctness, depth, real-world understanding, and confidence based strictly on the evidence in the QA transcript.
    - Assign a score out of 10. Do not inflate; be strict. (0-3 weak, 4-6 basic, 7-8 strong, 9-10 expert).
    - Provide a short justification paragraph based on transcript evidence.

    QA Transcript: {qa}
    Score: {overall_score}
    
    Return JSON: 
    {{ 
        "summary": "...", 
        "recommendation": "...", 
        "strengths": [], 
        "weaknesses": [], 
        "evaluated_skills": [
            {{ "skillName": "React", "score": 8.5, "justification": "Evidence here..." }}
        ],
        "detailed_feedback": "..." 
    }}
    """
    try:
        response = await call_openai_direct(prompt, "Generate professional HR report. Return valid JSON.")
        data = json.loads(clean_json(response))
        return {
            "overall_score": overall_score,
            "technical_skills_score": float(data.get("technical_score", 5)),
            "communication_score": float(data.get("communication_score", 5)),
            "problem_solving_score": float(data.get("problem_solving_score", 5)),
            "strengths": json.dumps(data.get("strengths", [])),
            "weaknesses": json.dumps(data.get("weaknesses", [])),
            "summary": data.get("summary", ""),
            "recommendation": data.get("recommendation", "consider"),
            "detailed_feedback": data.get("detailed_feedback", ""),
            "evaluated_skills": json.dumps(data.get("evaluated_skills", []))
        }
    except Exception as e:
        print(f"Report Gen Error: {e}")
        return {
            "overall_score": overall_score,
            "technical_skills_score": 0.0, "communication_score": 0.0, "problem_solving_score": 0.0,
            "strengths": "[]", "weaknesses": "[]", "summary": "Report gen failed", "recommendation": "consider", "detailed_feedback": "N/A"
        }


async def extract_questions_from_text(text: str) -> list:
    """Extract a list of interview questions from unstructured text using AI."""
    if not text.strip():
        return []
        
    system_prompt = (
        "You are an expert recruiter. You will be given raw text extracted from a document. "
        "Your task is to identify and extract all interview questions mentioned in the text. "
        "Return the questions as a CLEAN JSON list of strings. If no clear questions are found, return an empty list. "
        "Important: Return ONLY the JSON list, no preamble."
    )
    
    user_prompt = f"Text to extract questions from:\n\n{text[:5000]}"
    
    try:
        response = await call_openai_direct(user_prompt, system_prompt)
        cleaned = clean_json(response)
        data = json.loads(cleaned)
        if isinstance(data, list):
            return [str(q).strip() for q in data if q]
    except Exception as e:
        logger.error(f"Error extracting questions from text: {e}")
        
    return []

async def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe audio file using Groq Whisper-large-v3.
    """
    if not settings.groq_keys:
        raise Exception("GROQ_API_KEY is missing for transcription.")

    api_key = settings.groq_keys[0]
    base_url = "https://api.groq.com/openai/v1"
    
    # We use the standard AsyncOpenAI client as it's Groq-compatible
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=httpx.Timeout(30.0, connect=5.0)
    )

    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="json",
                language="en",
                temperature=0.0
            )
            return transcript.text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise e
