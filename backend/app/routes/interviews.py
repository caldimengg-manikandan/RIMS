from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
import json
import os
import random
from app.config import get_settings
from app.database import get_db
from app.models import User, Interview, Application, InterviewQuestion, InterviewAnswer, InterviewReport, Job
from app.schemas import (
    InterviewStart, InterviewAnswerSubmit, InterviewResponse, 
    InterviewQuestionResponse, InterviewDetailResponse, InterviewReportResponse,
    InterviewListResponse, InterviewAccess
)



from app.auth import get_current_user, get_current_hr, get_current_interview, pwd_context, create_access_token
from app.services.ai_service import (
    generate_adaptive_interview_question,
    evaluate_interview_answer,
    generate_interview_report,
    analyze_introduction,
    evaluate_detailed_answer,
    generate_domain_questions,
    generate_behavioral_question,
    generate_custom_domain_questions,
    generate_behavioral_batch,
    extract_questions_from_text,
    transcribe_audio
)
import tempfile
import shutil
from app.services.resume_parser import parse_content_from_path

# Import termination checker (reuse analyzer singleton from ai_service)
try:
    from backend.interview_process.response_analyzer import ResponseAnalyzer as _RA
except ImportError:
    from interview_process.response_analyzer import ResponseAnalyzer as _RA
_termination_checker = _RA()


router = APIRouter(prefix="/api/interviews", tags=["interviews"])
settings = get_settings()

from app.rate_limiter import limiter

# ─── Stage Constants ──────────────────────────────────────────────────────────
STAGE_APTITUDE = "aptitude"
STAGE_FIRST_LEVEL = "first_level"
STAGE_COMPLETED = "completed"

APTITUDE_QUESTION_COUNT = 10  # Number of aptitude questions to pick from uploaded file


def _determine_initial_stage(job: Job) -> str:
    """Determine the initial interview stage based on job configuration."""
    if job.aptitude_enabled and job.experience_level.lower() == "junior":
        return STAGE_APTITUDE
    return STAGE_FIRST_LEVEL


def _enforce_stage(interview: Interview, required_stage: str):
    """Raise 403 if the interview is not in the required stage."""
    if interview.interview_stage == STAGE_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This interview has been fully completed."
        )
    if interview.interview_stage != required_stage:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Current stage is '{interview.interview_stage}', but '{required_stage}' is required."
        )


async def _generate_aptitude_questions(interview: Interview, job: Job, db: Session):
    """Generate aptitude questions from uploaded file (random selection) or fallback defaults."""
    aptitude_prompts = []

    aptitude_mode = getattr(job, 'aptitude_mode', 'ai')
    
    if aptitude_mode == 'upload' and getattr(job, 'aptitude_questions_file', None):
        try:
            file_path = settings.base_dir / job.aptitude_questions_file
            if file_path.exists():
                # Robust reading for potential encoding issues
                uploaded_questions = None
                for encoding in ['utf-8-sig', 'latin-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            uploaded_questions = json.load(f)
                        break
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                
                if uploaded_questions is None:
                    # Fallback: Extract text and use AI to structure it
                    raw_text = parse_content_from_path(str(file_path))
                    if raw_text:
                        print(f"Non-JSON aptitude file detected. Extracting via AI...")
                        uploaded_questions = await extract_questions_from_text(raw_text)
                
                if uploaded_questions and isinstance(uploaded_questions, list) and len(uploaded_questions) > 0:
                    # Shuffle and pick N
                    random.shuffle(uploaded_questions)
                    selected = uploaded_questions[:APTITUDE_QUESTION_COUNT]
                    for item in selected:
                        if isinstance(item, dict) and 'question' in item:
                            # MCQ format: build question text with options
                            options = item.get('options', [])
                            q_text = item['question']
                            if options:
                                q_text += '\n' + '\n'.join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)])
                            aptitude_prompts.append(q_text)
                        elif isinstance(item, str):
                            aptitude_prompts.append(item)
        except Exception as e:
            print(f"Error loading uploaded aptitude questions: {e}")

    # Fallback/AI mode
    if not aptitude_prompts:
        if aptitude_mode == 'ai':
            from app.services.ai_service import generate_aptitude_batch
            try:
                # We request 10 questions for aptitude as per new requirements
                aptitude_prompts = await generate_aptitude_batch(10)
            except Exception as e:
                print(f"AI generation for aptitude failed: {e}")
                aptitude_prompts = []
                
        if not aptitude_prompts:
            default_prompts = [
                {
                    "question": "You have 5 machines that each produce 5 widgets in 5 minutes. How long would it take 100 machines to produce 100 widgets?",
                    "options": ["5 minutes", "100 minutes", "25 minutes", "1 minute"],
                    "answer": 0
                },
                {
                    "question": "If a train travels 60 km in the first hour and 40 km in the second hour, what is the average speed?",
                    "options": ["50 km/h", "45 km/h", "55 km/h", "60 km/h"],
                    "answer": 0
                },
                {
                    "question": "A is twice as old as B. 10 years ago, A was three times as old as B. How old is B now?",
                    "options": ["20", "15", "25", "30"],
                    "answer": 0
                },
                {
                    "question": "What comes next in the sequence: 2, 6, 12, 20, 30, ?",
                    "options": ["42", "40", "36", "44"],
                    "answer": 0
                },
                {
                    "question": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?",
                    "options": ["Yes", "No", "Maybe", "Depends on Bloops"],
                    "answer": 0
                },
                {
                    "question": "A farmer has 17 sheep. All but 9 die. How many are left?",
                    "options": ["9", "17", "8", "0"],
                    "answer": 0
                },
                {
                    "question": "You have a 3-liter jug and a 5-liter jug. How do you measure exactly 4 liters?",
                    "options": ["Fill 5L, pour to 3L, empty 3L, pour rem. 2L to 3L, fill 5L, pour to 3L", "Fill 3L twice", "Fill 5L once", "Not possible"],
                    "answer": 0
                },
                {
                    "question": "If it takes 5 hours for 5 people to dig 5 holes, how long does it take 1 person to dig 1 hole?",
                    "options": ["5 hours", "1 hour", "10 hours", "1/5 hour"],
                    "answer": 0
                },
                {
                    "question": "What is the next number: 1, 1, 2, 3, 5, 8, ?",
                    "options": ["13", "11", "15", "10"],
                    "answer": 0
                },
                {
                    "question": "A clock shows 3:15. What is the angle between the hour and minute hand?",
                    "options": ["7.5 degrees", "0 degrees", "15 degrees", "5 degrees"],
                    "answer": 0
                }
            ]
            random.shuffle(default_prompts)
            # Standardize exactly 10 questions per the spec
            aptitude_prompts = default_prompts[:10]

    try:
        for i, item in enumerate(aptitude_prompts):
            q_text = ""
            options = None
            correct = None
            
            if isinstance(item, dict):
                q_text = item.get("question", "")
                options = json.dumps(item.get("options", []))
                correct = item.get("answer", 0)
            else:
                q_text = str(item)

            q = InterviewQuestion(
                interview_id=interview.id,
                question_number=i + 1,
                question_text=q_text,
                options=options,
                correct_answer=str(correct) if correct is not None else None,
                question_type="aptitude"
            )
            db.add(q)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving aptitude questions: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate aptitude questions safely.")
    print(f"Generated {len(aptitude_prompts)} aptitude questions (sample test)")


async def _generate_first_level_questions(interview: Interview, job: Job, application, db: Session):
    """Generate first-level interview questions (existing logic)."""
    try:
        resume_extraction = application.resume_extraction
        resume_text = resume_extraction.extracted_text if resume_extraction else ""
        
        # 1. Analyze resume to lock skill and detect level
        analysis = await analyze_introduction(resume_text, job.title)
        locked_skill = analysis.get("primary_skill", "general")
        experience = analysis.get("experience", "mid")
        
        # Extract candidate skills from stored resume extraction
        candidate_skills = []
        if resume_extraction and resume_extraction.extracted_skills:
            try:
                candidate_skills = json.loads(resume_extraction.extracted_skills)
            except Exception:
                pass
        if not candidate_skills:
            skills_str = analysis.get("skills", "")
            if isinstance(skills_str, str) and skills_str:
                candidate_skills = [s.strip() for s in skills_str.split(',')]
            elif isinstance(skills_str, list):
                candidate_skills = skills_str

        print(f"🔒 Skill: {locked_skill} | Level: {experience} | Skills: {candidate_skills}")
        interview.locked_skill = locked_skill
        db.add(interview)
        db.commit()

        # 2. Level-based question split
        level_lower = experience.lower()
        if "senior" in level_lower or "lead" in level_lower or "manager" in level_lower:
            basic_count, deep_count = 2, 8
        elif "junior" in level_lower or "intern" in level_lower or "fresh" in level_lower:
            basic_count, deep_count = 8, 2
        else:
            basic_count, deep_count = 5, 5

        # 3. Handle Question Generation Modes
        interview_mode = getattr(job, 'interview_mode', 'ai') or 'ai'
        uploaded_tech = []
        uploaded_behav = []
        
        if interview_mode in ['upload', 'mixed']:
            file_name = getattr(job, 'uploaded_question_file', None)
            if not file_name:
                raise HTTPException(status_code=400, detail="Uploaded question file is missing for the selected mode.")
            
            file_path = settings.base_dir / file_name
            if not file_path.exists():
                raise HTTPException(status_code=400, detail="Uploaded question file not found on server.")
                
            try:
                import json
                # Robust reading for potential encoding issues
                data = None
                for encoding in ['utf-8-sig', 'latin-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            data = json.load(f)
                        break
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                
                if data is None:
                     # Fallback: Extract text and use AI to structure it
                     raw_text = parse_content_from_path(str(file_path))
                     if raw_text:
                         print(f"Non-JSON question file detected. Extracting via AI...")
                         data = await extract_questions_from_text(raw_text)
                     else:
                         raise ValueError("File is not a valid JSON list or has invalid encoding, and text extraction failed.")
                
                if not isinstance(data, list):
                    raise ValueError("File content is not a list")
                    
                for item in data:
                    if isinstance(item, dict) and 'question' in item:
                        q_text = item['question']
                        q_type = str(item.get('type', 'technical')).lower()
                        options = item.get('options', [])
                        if options:
                            q_text += '\n' + '\n'.join([f"{chr(65+j)}) {opt}" for j, opt in enumerate(options)])
                        
                        if 'behavioral' in q_type:
                            uploaded_behav.append(q_text)
                        else:
                            uploaded_tech.append(q_text)
                    elif isinstance(item, str):
                        uploaded_tech.append(item)
                        
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Uploaded question file is corrupt: {str(e)}")
            
            if not uploaded_tech and not uploaded_behav:
                raise HTTPException(status_code=400, detail="Uploaded question file contains no valid questions.")
                
        # Offset question numbers based on whether aptitude was done
        q_offset = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview.id
        ).count()

        tech_questions = []
        behav_questions = []
        behavioral_role = getattr(job, 'behavioral_role', "general")

        if interview_mode == 'upload':
            tech_questions = uploaded_tech[:15]
            behav_questions = uploaded_behav[:5]
            
            # Fill missing technical via AI (if file had < 15 tech)
            missing_tech = 15 - len(tech_questions)
            if missing_tech > 0:
                print(f"Upload mode: filling {missing_tech} missing technical questions via AI")
                ai_tech = await generate_custom_domain_questions(
                    locked_skill, missing_tech, "basic", candidate_skills, job.primary_evaluated_skills
                )
                tech_questions.extend(ai_tech)
                
            # Fill missing behavioral via AI (if file had < 5 behav)
            missing_behav = 5 - len(behav_questions)
            if missing_behav > 0:
                print(f"Upload mode: filling {missing_behav} missing behavioral questions via AI")
                ai_behav = await generate_behavioral_batch(missing_behav, behavioral_role=behavioral_role)
                behav_questions.extend(ai_behav)
                
        elif interview_mode == 'mixed':
            import random
            random.shuffle(uploaded_tech)
            tech_questions = uploaded_tech[:10]
            
            # Fill remaining 5 tech via AI
            missing_tech = 15 - len(tech_questions)
            print(f"Mixed mode: using {len(tech_questions)} uploaded tech, generating {missing_tech} AI tech")
            if missing_tech > 0:
                ai_tech = await generate_custom_domain_questions(
                    locked_skill, missing_tech, "basic", candidate_skills, job.primary_evaluated_skills
                )
                tech_questions.extend(ai_tech)
                
            # Always generate 5 behavioral via AI for mixed
            print(f"Mixed mode: generating 5 AI behavioral questions")
            behav_questions = await generate_behavioral_batch(5, behavioral_role=behavioral_role)
            
        else:
            # Default AI Mode
            total_basic_count = 5 + basic_count
            all_basic = await generate_custom_domain_questions(
                locked_skill, total_basic_count, "basic", candidate_skills, job.primary_evaluated_skills
            )
            questions_q1_q5 = all_basic[:5]
            questions_mid_basic = all_basic[5:]
    
            questions_mid_deep = await generate_custom_domain_questions(
                locked_skill, deep_count, "scenario-based/followup", candidate_skills, job.primary_evaluated_skills
            )
            print(f"AI Mode Q1-Q5: {len(questions_q1_q5)} | Q6-Q15 basic: {len(questions_mid_basic)} deep: {len(questions_mid_deep)}")
    
            tech_questions = questions_q1_q5 + questions_mid_basic + questions_mid_deep
            behav_questions = await generate_behavioral_batch(5, behavioral_role=behavioral_role)
            print(f"AI Mode Q16-Q20: {len(behav_questions)} behavioral")

        all_questions = tech_questions + behav_questions

        # Save all questions to DB with proper numbering
        for i, q_text in enumerate(all_questions):
            q_num = q_offset + i + 1
            q_type = "behavioral" if i >= (len(all_questions) - 5) else "technical"
            q = InterviewQuestion(
                interview_id=interview.id,
                question_number=q_num,
                question_text=q_text,
                question_type=q_type,
                options=None,
                correct_answer=None
            )
            db.add(q)

        interview.total_questions = q_offset + len(all_questions)
        db.add(interview)
        db.commit()
        print(f"✅ {len(all_questions)} first-level questions saved (offset={q_offset})")

    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException):
            raise e  # Do not fallback if it's an explicit validation error
            
        print(f"Error generating first-level questions: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback questions — maintain full 15 technical + 5 behavioral = 20 structure
        q_offset = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview.id
        ).count()
        
        # 15 Technical fallback questions (Q1-Q15)
        technical_fallbacks = [
            "Please describe your professional background and key technical skills.",
            "Describe a challenging project you worked on.",
            "What are the most important technical skills in your domain?",
            "How do you approach debugging a production issue?",
            "Explain a complex system you have built or contributed to.",
            "How do you ensure code quality in your work?",
            "Describe your experience with version control systems and CI/CD pipelines.",
            "How do you handle performance optimization in your projects?",
            "What is your approach to writing maintainable and scalable code?",
            "Describe a time when you had to learn a new technology quickly.",
            "How do you approach system design and architecture decisions?",
            "What testing strategies do you use in your development process?",
            "How do you handle technical debt in a project?",
            "Describe your experience working with APIs and integrations.",
            "How do you stay updated on new technologies and best practices?",
        ]
        
        # 5 Behavioral fallback questions (Q16-Q20)
        behavioral_fallbacks = [
            "Tell me about a time you faced an unexpected challenge at work.",
            "Describe a situation where you had to collaborate with a difficult team member.",
            "How do you handle tight deadlines and competing priorities?",
            "Tell me about a time you received constructive feedback and how you responded.",
            "Describe a situation where you took initiative beyond your assigned responsibilities.",
        ]
        
        all_fallbacks = technical_fallbacks + behavioral_fallbacks
        
        for i, q_text in enumerate(all_fallbacks):
            q_type = "behavioral" if i >= len(technical_fallbacks) else "technical"
            q = InterviewQuestion(
                interview_id=interview.id,
                question_number=q_offset + i + 1,
                question_text=q_text,
                question_type=q_type
            )
            db.add(q)
        try:
            interview.total_questions = q_offset + len(all_fallbacks)
            db.add(interview)
            db.commit()
            print(f"⚠️ Fallback: Generated {len(all_fallbacks)} questions ({len(technical_fallbacks)} technical + {len(behavioral_fallbacks)} behavioral)")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to generate fallback questions safely.")


@router.post("/access")
@limiter.limit("3/minute")
async def access_interview(
    request: Request,
    data: InterviewAccess,
    db: Session = Depends(get_db)
):
    """Access an interview session securely using one-time key"""
    applications = db.query(Application).filter(Application.candidate_email == data.email.lower().strip()).all()
    if not applications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    application_ids = [app.id for app in applications]
    interviews = db.query(Interview).filter(Interview.application_id.in_(application_ids)).all()
    
    if not interviews:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
        
    matched_interview = None
    for inv in interviews:
        if pwd_context.verify(data.access_key, inv.access_key_hash):
            matched_interview = inv
            break
            
    if not matched_interview:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access key")
    
    # Re-read with row-level lock to prevent key replay race condition
    interview = db.query(Interview).filter(
        Interview.id == matched_interview.id
    ).with_for_update().first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    if interview.is_used:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Interview access key has already been used")
        
    # Ensure the DB timestamp has timezone info before comparing (SQLite returns naive)
    expires_at = interview.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Interview access key has expired")
        
    application = interview.application
    job = application.job
    
    # Atomic mark as used and start
    try:
        interview.is_used = True
        interview.used_at = datetime.now(timezone.utc)
        interview.status = "in_progress"
        interview.interview_stage = _determine_initial_stage(job)
        
        # STRICT ROLE-BASED FLOW ENFORCEMENT
        # Only Junior roles (if enabled) start at aptitude. 
        # Non-junior seamlessly bypass aptitude.
        if job.experience_level.lower() != "junior" and interview.interview_stage == STAGE_APTITUDE:
            interview.interview_stage = STAGE_FIRST_LEVEL

        if not interview.started_at:
            interview.started_at = datetime.now(timezone.utc)
            interview.duration_minutes = job.duration_minutes or 60
            
        print(f"Starting interview session for ID {interview.id} (atomic transaction)")
    except Exception as e:
        db.rollback()
        print(f"Pre-flight setup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate interview safety protocol.")
    
    from datetime import timedelta
    token = create_access_token(
        data={"sub": str(interview.id), "role": "interview"},
        expires_delta=timedelta(hours=2)
    )
    
    # Generate questions safely — pre-generate ALL stages at access time
    # This eliminates AI latency during stage transitions (complete_aptitude)
    try:
        if interview.interview_stage == STAGE_APTITUDE:
            await _generate_aptitude_questions(interview, job, db)
            # PRE-GENERATE first-level questions now so they're ready when aptitude completes
            if job.first_level_enabled:
                await _generate_first_level_questions(interview, job, application, db)
        else:
            await _generate_first_level_questions(interview, job, application, db)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error during atomic startup: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed during safe question generation.")
    
    # FINAL COMMIT: Only if everything (including AI) succeeded
    db.commit()
    db.refresh(interview)
    
    print(f"🚀 Interview {interview.id} successfully started and questions saved.")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "interview_id": interview.id,
        "interview_stage": interview.interview_stage,
    }


@router.get("/{interview_id}/stage")
async def get_interview_stage(
    interview_id: int,
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """Get the current pipeline stage for the interview."""
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    job = interview_session.application.job
    return {
        "id": interview_session.id,
        "status": interview_session.status,
        "interview_stage": interview_session.interview_stage,
        "locked_skill": interview_session.locked_skill,
        "total_questions": interview_session.total_questions or 0,
        "aptitude_enabled": job.aptitude_enabled if job else False,
        "first_level_enabled": job.first_level_enabled if job else True,
        "aptitude_score": interview_session.aptitude_score,
        "aptitude_completed_at": interview_session.aptitude_completed_at,
        "started_at": interview_session.started_at,
        "duration_minutes": interview_session.duration_minutes,
    }


@router.get("/{interview_id}/questions")
async def get_all_questions(
    interview_id: int,
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """Get ALL questions for the interview (all stages)."""
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.question_number).all()

    # Batch-load answered status
    question_ids = [q.id for q in questions]
    answered_ids = set(
        row[0] for row in db.query(InterviewAnswer.question_id).filter(
            InterviewAnswer.question_id.in_(question_ids)
        ).all()
    ) if question_ids else set()

    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "interview_id": q.interview_id,
            "question_number": q.question_number,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "question_options": q.options,
            "is_answered": q.id in answered_ids
        })
    return result


@router.get("/{interview_id}/current-question", response_model=InterviewQuestionResponse)
async def get_current_question(
    interview_id: int,
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """Get current unanswered question for the current stage."""
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
    interview = interview_session
    
    if interview.interview_stage == STAGE_COMPLETED:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Interview fully completed")

    if interview.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Interview complete")
    
    # Filter by current stage
    query = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    )
    if interview.interview_stage == STAGE_APTITUDE:
        query = query.filter(InterviewQuestion.question_type == "aptitude")
    else:
        query = query.filter(InterviewQuestion.question_type != "aptitude")
    
    questions = query.order_by(InterviewQuestion.question_number).all()
    
    # Batch-load answered IDs in ONE query (eliminates N+1)
    question_ids = [q.id for q in questions]
    answered_ids = set(
        row[0] for row in db.query(InterviewAnswer.question_id).filter(
            InterviewAnswer.question_id.in_(question_ids)
        ).all()
    ) if question_ids else set()
    
    for question in questions:
        if question.id not in answered_ids:
            # Manually map to schema to avoid AttributeError if model lacks question_options
            return {
                "id": question.id,
                "interview_id": question.interview_id,
                "question_number": question.question_number,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "question_options": question.options,
                "options": question.options
            }
            
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="All questions in this stage answered")


@router.post("/{interview_id}/submit-answer")
async def submit_answer(
    interview_id: int,
    data: InterviewAnswerSubmit,
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """Submit answer to current question (stage-aware)."""
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        
    interview = interview_session
    
    if interview.interview_stage == STAGE_COMPLETED:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Interview fully completed")

    # Use the explicit question_id from the request
    current_question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == data.question_id,
        InterviewQuestion.interview_id == interview_id
    ).first()
    
    if not current_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Check if already answered - make idempotent
    existing_answer = db.query(InterviewAnswer).filter(
        InterviewAnswer.question_id == data.question_id
    ).first()
    if existing_answer:
        return {"success": True, "answer_id": existing_answer.id}
    
    # ── Termination check (abusive language / explicit quit) ──────────────────
    # Only run for technical/behavioral — aptitude answers are naturally very short
    should_terminate = False
    termination_reason = ""
    if (current_question.question_type or "").lower() != "aptitude":
        should_terminate, termination_reason = _termination_checker.check_for_termination(
            data.answer_text, 
            question_type=current_question.question_type
        )

    if should_terminate:
        try:
            interview.status = "terminated"
            interview.interview_stage = STAGE_COMPLETED
            interview.ended_at = datetime.now(timezone.utc)
            interview.application.status = "interview_completed"  # closest valid status
            db.commit()
        except Exception:
            db.rollback()
        return {
            "success": True,
            "terminated": True,
            "termination_reason": termination_reason,
            "message": (
                "Interview terminated due to inappropriate language."
                if termination_reason == "misconduct"
                else "Interview ended at your request."
            )
        }
    # ─────────────────────────────────────────────────────────────────────────


    try:
        # Save answer (unique constraint on question_id prevents duplicates)
        answer = InterviewAnswer(
            question_id=current_question.id,
            interview_id=interview_id,
            answer_text=data.answer_text,
            submitted_at=datetime.now(timezone.utc)
        )

        # Auto-grade aptitude MCQs if correct_answer is set
        if current_question.question_type == "aptitude" and current_question.correct_answer is not None:
            # Assume answer_text is the option index (0, 1, 2, 3) or the text
            submitted_val = data.answer_text.strip()
            is_correct = False
            try:
                if int(submitted_val) == int(current_question.correct_answer):
                    is_correct = True
            except (ValueError, TypeError):
                # If they submitted text instead of index, try to match it
                if current_question.options:
                    try:
                        options = json.loads(current_question.options)
                        correct_idx = int(current_question.correct_answer)
                        if isinstance(options, list) and correct_idx < len(options):
                            if submitted_val.lower() == options[correct_idx].lower():
                                is_correct = True
                    except:
                        pass
            
            answer.answer_score = 10.0 if is_correct else 0.0
            answer.skill_relevance_score = 10.0 if is_correct else 0.0
            answer.evaluated_at = datetime.now(timezone.utc)
            answer.answer_evaluation = json.dumps({"auto_graded": True, "is_correct": is_correct})

        db.add(answer)
        db.commit()
        db.refresh(answer)
    except IntegrityError:
        db.rollback()
        # Duplicate answer — return the existing one idempotently
        existing = db.query(InterviewAnswer).filter(
            InterviewAnswer.question_id == current_question.id
        ).first()
        if existing:
            return {"success": True, "answer_id": existing.id}
        raise HTTPException(status_code=409, detail="Answer already submitted for this question.")
    except Exception as e:
        db.rollback()
        detail = f"Failed to save answer: {str(e)}" if settings.debug else "Failed to save answer efficiently."
        raise HTTPException(status_code=500, detail=detail)
    
    # Evaluate answer with AI safely (non-blocking failure)
    # Skip AI evaluation for aptitude (MCQs are auto-graded above)
    if current_question.question_type == "aptitude":
        return {"success": True, "answer_id": answer.id}

    try:
        # Get detailed evaluation
        try:
            # Pass question type so AI service knows whether to run technical or behavioral eval
            evaluation = await ai_service.evaluate_detailed_answer(
                current_question.question_text, 
                data.answer_text,
                question_type=current_question.question_type or "technical"
            )
            
            if current_question.question_type == "behavioral":
                # Map behavioral specific keys to generic DB columns
                # We store the real keys in the answer_evaluation JSON
                technical_score = evaluation.get("relevance", 0)
                completeness_score = evaluation.get("action_impact", 0)
                clarity_score = evaluation.get("clarity", 0)
                depth_score = 0
                practicality_score = 0
            else:
                technical_score = evaluation.get("technical_accuracy", 0)
                completeness_score = evaluation.get("completeness", 0)
                clarity_score = evaluation.get("clarity", 0)
                depth_score = evaluation.get("depth", 0)
                practicality_score = evaluation.get("practicality", 0)
            
            answer_score = evaluation.get("overall", 0)
            answer_evaluation = json.dumps(evaluation)
        except Exception as e:
            print(f"Error evaluating detailed answer: {e}")
            # Fallback scores
            answer_score = 5.0
            technical_score = 5.0
            completeness_score = 5.0
            clarity_score = 5.0
            depth_score = 5.0
            practicality_score = 5.0
            answer_evaluation = json.dumps({"error": "Evaluation failed"})

        answer.answer_score = float(answer_score)
        answer.skill_relevance_score = float(technical_score) # Using technical_score for skill_relevance
        answer.technical_score = float(technical_score)
        answer.completeness_score = float(completeness_score)
        answer.clarity_score = float(clarity_score)
        answer.depth_score = float(depth_score)
        answer.practicality_score = float(practicality_score)
        answer.answer_evaluation = answer_evaluation
        answer.evaluated_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error evaluating answer safely: {e}")
    
    return {"success": True, "answer_id": answer.id}


@router.post("/{interview_id}/complete-aptitude")
async def complete_aptitude(
    interview_id: int,
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """
    Complete the aptitude round and automatically transition to first-level interview.
    Calculates aptitude score, generates first-level questions, and returns the first question.
    NO re-login required — same session continues.
    """
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Re-read with row-level lock to prevent double-click race
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).with_for_update().first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    # Idempotency guard: if already past aptitude, return success
    if interview.interview_stage != STAGE_APTITUDE:
        return {
            "success": True,
            "aptitude_score": interview.aptitude_score,
            "new_stage": interview.interview_stage,
            "message": "Aptitude round already completed.",
        }
    
    _enforce_stage(interview, STAGE_APTITUDE)

    # Verify all aptitude questions are answered — batch query (no N+1)
    aptitude_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id,
        InterviewQuestion.question_type == "aptitude"
    ).all()

    apt_q_ids = [q.id for q in aptitude_questions]
    answered_q_ids = set()
    if apt_q_ids:
        answered = db.query(InterviewAnswer.question_id).filter(
            InterviewAnswer.question_id.in_(apt_q_ids)
        ).all()
        answered_q_ids = {row[0] for row in answered}

    unanswered = [q for q in aptitude_questions if q.id not in answered_q_ids]
    if unanswered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All aptitude questions must be answered before completing the aptitude round."
        )

    # Calculate aptitude score for display purposes (does not affect final combined score)
    answers = db.query(InterviewAnswer).filter(
        InterviewAnswer.question_id.in_(apt_q_ids)
    ).all() if apt_q_ids else []
    
    apt_scores = [a.answer_score for a in answers if a.answer_score is not None]
    if apt_scores:
        interview.aptitude_score = sum(apt_scores) / len(apt_scores)
    else:
        interview.aptitude_score = 0.0

    interview.aptitude_completed_at = datetime.now(timezone.utc)
    interview.aptitude_completed = True

    job = interview.application.job

    # Check if first_level is enabled
    if job.first_level_enabled:
        try:
            # Transition to first-level interview
            # Questions were PRE-GENERATED during access_interview — no AI delay here
            interview.interview_stage = STAGE_FIRST_LEVEL
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed changing pipeline stages.")

        # Get the first question to return
        first_q = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_type != "aptitude"
        ).order_by(InterviewQuestion.question_number).first()

        return {
            "success": True,
            "aptitude_score": interview.aptitude_score,
            "new_stage": STAGE_FIRST_LEVEL,
            "message": "Aptitude round completed. First-level interview questions generated.",
            "first_question": {
                "id": first_q.id,
                "question_number": first_q.question_number,
                "question_text": first_q.question_text,
                "question_type": first_q.question_type,
            } if first_q else None,
        }
    else:
        try:
            # Aptitude only — mark as completed
            interview.interview_stage = STAGE_COMPLETED
            interview.status = "completed"
            interview.ended_at = datetime.now(timezone.utc)
            interview.overall_score = interview.aptitude_score
            interview.application.status = "interview_completed"
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to finalise aptitude round.")

        # Generate minimal InterviewReport for aptitude-only jobs
        try:
            existing_report = db.query(InterviewReport).filter(
                InterviewReport.interview_id == interview_id
            ).first()
            if not existing_report:
                report = InterviewReport(
                    interview_id=interview_id,
                    candidate_name=interview.application.candidate_name,
                    candidate_email=interview.application.candidate_email,
                    applied_role=job.title,
                    overall_score=interview.aptitude_score or 0.0,
                    technical_skills_score=0,
                    communication_score=0,
                    problem_solving_score=0,
                    strengths="[]",
                    weaknesses="[]",
                    summary="Aptitude-only interview completed. No first-level interview configured.",
                    recommendation="consider",
                    detailed_feedback="Aptitude round completed successfully.",
                    aptitude_score=interview.aptitude_score,
                    combined_score=interview.aptitude_score or 0.0,
                )
                db.add(report)
                db.commit()
        except Exception as e:
            print(f"Error creating aptitude-only report: {e}")

        return {
            "success": True,
            "aptitude_score": interview.aptitude_score,
            "new_stage": STAGE_COMPLETED,
            "message": "Aptitude round completed. No first-level interview configured for this job.",
        }


@router.post("/{interview_id}/end")
async def end_interview(
    interview_id: int,
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """End first-level interview and trigger final evaluation."""
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Re-read with row-level lock to prevent double-click race
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).with_for_update().first()
    
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    # Handle transition if still in aptitude or mixed stage (Unified Flow)
    if interview.interview_stage == STAGE_APTITUDE:
        # Calculate/Sync Aptitude Score before finishing
        apt_questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_type == "aptitude"
        ).all()
        apt_q_ids = [q.id for q in apt_questions]
        if apt_q_ids:
            answers = db.query(InterviewAnswer).filter(InterviewAnswer.question_id.in_(apt_q_ids)).all()
            answered_ids = {a.question_id for a in answers}
            if len(answered_ids) < len(apt_questions):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"All {len(apt_questions)} aptitude questions must be answered before ending."
                )
            # Set aptitude score
            apt_scores = [a.answer_score for a in answers if a.answer_score is not None]
            interview.aptitude_score = sum(apt_scores) / len(apt_scores) if apt_scores else 0.0
            interview.aptitude_completed_at = datetime.now(timezone.utc)
            interview.aptitude_completed = True

    # Idempotency guard: if already completed, return success
    if interview.interview_stage == STAGE_COMPLETED:
        return {
            "success": True,
            "interview_id": interview_id,
            "status": "already_completed",
            "interview_score": interview.overall_score,
            "aptitude_score": interview.aptitude_score,
            "combined_score": interview.overall_score,
        }
    
    # Mark completed
    interview.status = "completed"
    interview.interview_stage = STAGE_COMPLETED
    interview.ended_at = datetime.now(timezone.utc)
    interview.application.status = "interview_completed"
    
    # Calculate overall interview score (first-level questions only)
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id,
        InterviewQuestion.question_type != "aptitude"
    ).all()
    
    scores = []
    behavioral_scores = []
    qa_pairs = []
    
    for question in questions:
        answers = db.query(InterviewAnswer).filter(
            InterviewAnswer.question_id == question.id
        ).order_by(InterviewAnswer.id).all()
        if answers:
            latest_answer = answers[-1]
            score = latest_answer.answer_score if latest_answer.answer_score is not None else 2.0
            
            # Split off Behavioral Questions (Q16+ / behavioral type)
            if question.question_type == 'behavioral' or question.question_number >= 16:
                behavioral_scores.append(score)
            else:
                scores.append(score)
                
            qa_pairs.append({
                "question": question.question_text,
                "answer": latest_answer.answer_text,
                "score": score,
                "evaluation_raw": latest_answer.answer_evaluation,
                "question_type": question.question_type
            })
    
    interview_score = sum(scores) / len(scores) if scores else 0.0
    behavioral_score = sum(behavioral_scores) / len(behavioral_scores) if behavioral_scores else 0.0
    
    # ENFORCEMENT: Ensure all technical/behavioral questions were answered before ending
    total_non_aptitude_answers = len(scores) + len(behavioral_scores)
    if total_non_aptitude_answers < len(questions) and len(questions) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All {len(questions)} technical/behavioral questions must be answered before ending."
        )

    try:
        interview.overall_score = interview_score
        interview.questions_asked = len(questions)
        interview.first_level_completed = True
        interview.first_level_score = interview_score
        interview.status = "completed"
        interview.ended_at = datetime.now(timezone.utc)
        
        # Final score = first-level interview score ONLY
        # Aptitude is a sample test and does NOT contribute to the final score
        aptitude_score = interview.aptitude_score  # stored for logging only, may be None
        combined_score = interview_score  # aptitude excluded from scoring
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to properly calculate intermediate scoring.")
    
    # Generate report
    try:
        job = interview.application.job
        primary_skills = []
        if getattr(job, 'primary_evaluated_skills', None):
            try:
                parsed = json.loads(job.primary_evaluated_skills)
                if isinstance(parsed, list):
                    primary_skills = parsed
            except:
                pass

        report_data = await generate_interview_report(
            job_title=job.title,
            all_qa_pairs=qa_pairs,
            overall_score=interview_score,
            primary_evaluated_skills=primary_skills
        )
        
        # Serialize detailed_feedback
        detailed_feedback_val = report_data["detailed_feedback"]
        if isinstance(detailed_feedback_val, (dict, list)):
            detailed_feedback_val = json.dumps(detailed_feedback_val)
            
        rec_raw = str(report_data.get("recommendation", "consider")).lower()
        if "not " in rec_raw or "not_recommended" in rec_raw:
            rec_val = "not_recommended"
        elif "recommend" in rec_raw:
            rec_val = "recommended"
        else:
            rec_val = "consider"
            
        report = InterviewReport(
            interview_id=interview_id,
            candidate_name=interview.application.candidate_name,
            candidate_email=interview.application.candidate_email,
            applied_role=job.title,
            overall_score=report_data["overall_score"],
            technical_skills_score=report_data.get("technical_skills_score", 5),
            communication_score=report_data.get("communication_score", 5),
            problem_solving_score=report_data.get("problem_solving_score", 5),
            strengths=report_data.get("strengths", "[]"),
            weaknesses=report_data.get("weaknesses", "[]"),
            summary=report_data.get("summary", ""),
            recommendation=rec_val,
            detailed_feedback=detailed_feedback_val,
            aptitude_score=aptitude_score,
            behavioral_score=behavioral_score,
            combined_score=combined_score,
            evaluated_skills=report_data.get("evaluated_skills", "[]"),
        )
        
        db.add(report)
        db.commit()

        # Send notification to HR
        from app.models import Notification
        try:
            apt_info = f" | Aptitude: {aptitude_score:.1f}" if aptitude_score is not None else ""
            notification = Notification(
                user_id=job.hr_id,
                notification_type="interview_completed",
                title=f"Interview Completed: {interview.application.candidate_name}",
                message=f"{interview.application.candidate_name} completed the interview for {job.title}. Score: {combined_score:.1f}{apt_info}",
                related_application_id=interview.application_id,
                related_interview_id=interview_id
            )
            db.add(notification)
            db.commit()
        except Exception as e:
            print(f"Error creating notification: {e}")

    except Exception as e:
        import traceback
        with open(settings.logs_dir / "error_debug.log", "a", encoding="utf-8") as f:
            f.write(f"Error in end_interview: {e}\n{traceback.format_exc()}\n")
        print(f"Error generating report: {e}")
    
    return {
        "success": True,
        "interview_id": interview_id,
        "status": "completed",
        "interview_score": interview_score,
        "aptitude_score": aptitude_score,
        "combined_score": combined_score,
    }

@router.get("/{interview_id}", response_model=InterviewDetailResponse)
def get_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview details"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    
    return interview

@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
def get_interview_report(
    interview_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get interview report (HR only)"""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    
    report = db.query(InterviewReport).filter(
        InterviewReport.interview_id == interview_id
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not yet available"
        )
    
    # Return report data plus video_url from interview
    report_dict = {column.name: getattr(report, column.name) for column in report.__table__.columns}
    report_dict['video_url'] = interview.video_recording_path
    
    return report_dict

@router.post("/{interview_id}/transcribe")
async def transcribe_interview_audio(
    interview_id: int,
    file: UploadFile = File(...),
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """
    Transcribe audio recorded during an interview.
    """
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    # Secure temporary file handling
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        try:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        finally:
            file.file.close()

    try:
        text = await transcribe_audio(tmp_path)
        return {"text": text}
    except Exception as e:
        print(f"Transcription failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to process voice audio.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/{interview_id}/upload-video")
async def upload_interview_video(
    interview_id: int,
    file: UploadFile = File(...),
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """
    Upload the recorded video for the interview session.
    """
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Generate a unique filename: interview_{id}_{timestamp}.webm
    timestamp = int(datetime.now(timezone.utc).timestamp())
    filename = f"interview_{interview_id}_{timestamp}.webm"
    file_path = settings.videos_dir / filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Save relative path to DB
        # Note: We store the path that will be used by the static server
        relative_path = f"uploads/videos/{filename}"
        interview_session.video_recording_path = relative_path
        db.add(interview_session)
        db.commit()

        return {"success": True, "path": relative_path}
    except Exception as e:
        print(f"Video upload failure: {e}")
        raise HTTPException(status_code=500, detail="Failed to save video recording.")
    finally:
        file.file.close()
