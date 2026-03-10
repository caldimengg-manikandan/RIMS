from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import json
from app.database import get_db
from app.models import User, Interview, Application, InterviewQuestion, InterviewAnswer, InterviewReport, Job
from app.schemas import (
    InterviewStart, InterviewAnswerSubmit, InterviewResponse, 
    InterviewQuestionResponse, InterviewDetailResponse, InterviewReportResponse,
    InterviewListResponse
)
from app.auth import get_current_user, get_current_candidate, get_current_hr
from app.services.ai_service import (
    evaluate_interview_answer,
    generate_interview_report,
    analyze_introduction,
    evaluate_detailed_answer,
    generate_custom_domain_questions,
    generate_behavioral_batch
)

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

@router.get("/my-interviews", response_model=list[InterviewListResponse])
def get_my_interviews(
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """Get candidate's own interviews"""
    interviews = db.query(Interview).filter(
        Interview.candidate_id == current_user.id
    ).all()
    
    results = []
    for i in interviews:
        results.append({
            "id": i.id,
            "status": i.status,
            "created_at": i.created_at,
            "job_id": i.application.job_id,
            "job_title": i.application.job.title,
            "locked_skill": i.locked_skill,
            "score": i.overall_score
        })
    return results

@router.post("/start", response_model=InterviewResponse)
async def start_interview(
    data: InterviewStart,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """Start interview (Candidate only, after application approved)"""
    # Check if application exists and is approved
    application = db.query(Application).filter(
        Application.id == data.application_id,
        Application.candidate_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != "approved_for_interview":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Application must be approved before starting interview"
        )

    if not application.resume_file_path:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resume must be uploaded"
        )

    # Check if interview already exists
    existing_interview = db.query(Interview).filter(
        Interview.application_id == data.application_id
    ).first()
    
    if existing_interview:
        # If interview exists and is in progress, return it (allow resume)
        if existing_interview.status == "in_progress":
            return existing_interview
        
        # Prevent attempting to create a new interview if one is already completed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An interview for this application has already been completed."
        )
    
    # Create new interview
    try:
        print(f"Creating new interview for App ID: {data.application_id}")
        interview = Interview(
            application_id=data.application_id,
            candidate_id=current_user.id,
            status="in_progress",
            started_at=datetime.utcnow(),
            total_questions=20
        )
        
        db.add(interview)
        db.commit()
        db.refresh(interview)
        print(f"Interview record created with ID: {interview.id}")
        
        # Generate first question
        # Generate ALL questions upfront (Legacy Logic Port)
        try:
            job = application.job
            resume_extraction = application.resume_extraction
            resume_text = resume_extraction.extracted_text if resume_extraction else ""
            print(f"Resume text length: {len(resume_text)}")
            
            # 1. Analyze Intro/Resume to Lock Skill
            print("Analyzing resume for skills...")
            analysis = await analyze_introduction(resume_text, job.title)
            locked_skill = analysis.get("primary_skill", "general")
            experience = analysis.get("experience", "mid")
            
            # Extract the raw list of candidate skills parsed by the AI
            candidate_skills = []
            
            # Prefer the comprehensive skills list extracted during resume upload
            import json
            if resume_extraction and resume_extraction.extracted_skills:
                try:
                    candidate_skills = json.loads(resume_extraction.extracted_skills)
                except Exception:
                    pass
            
            # Fallback to the real-time analysis if not found
            if not candidate_skills:
                skills_str = analysis.get("skills", "")
                if isinstance(skills_str, str) and skills_str:
                    candidate_skills = [s.strip() for s in skills_str.split(',')]
                elif isinstance(skills_str, list):
                    candidate_skills = skills_str
            
            print(f"🔒 Locking interview to skill: {locked_skill} ({experience})")
            print(f"Candidate exact skills: {candidate_skills}")
            
            # Save locked skill + candidate analysis metadata
            interview.locked_skill = locked_skill
            interview.candidate_metadata = json.dumps({
                "experience": experience,
                "confidence": analysis.get("confidence", "N/A"),
                "communication": analysis.get("communication", "N/A"),
                "intro_score": analysis.get("intro_score", 0),
                "skills": candidate_skills
            })
            db.add(interview)
            db.commit()
            
            # 2. Generate Questions (20 Total)
            print(f"Generating 20 questions for level: {experience}")
            
            # Q6-Q15: 10 Technical Questions (Mixed based on Level)
            level_lower = experience.lower()
            
            if "senior" in level_lower or "lead" in level_lower or "manager" in level_lower:
                # Senior: 2 Basic + 8 Follow-up
                basic_count = 2
                deep_count = 8
            elif "junior" in level_lower or "intern" in level_lower or "fresh" in level_lower:
                # Junior: 8 Basic + 2 Follow-up
                basic_count = 8
                deep_count = 2
            else:
                # Mid (Default): 5 Basic + 5 Follow-up
                basic_count = 5
                deep_count = 5
                
            # Generate total basic questions all at once to prevent duplicates
            total_basic_count = 5 + basic_count
            all_basic_questions = await generate_custom_domain_questions(locked_skill, total_basic_count, "basic", candidate_skills)
            questions_q1_q5 = all_basic_questions[:5]
            questions_mid_basic = all_basic_questions[5:]

            questions_mid_deep = await generate_custom_domain_questions(locked_skill, deep_count, "scenario-based/followup", candidate_skills)
            print(f"Generated Q1-Q5: {len(questions_q1_q5)}")
            print(f"Generated Q6-Q15: {len(questions_mid_basic)} basic, {len(questions_mid_deep)} deep/followup")
            
            questions_q6_q15 = questions_mid_basic + questions_mid_deep
            
            # Q16-Q20: 5 Behavioral Questions
            questions_q16_q20 = await generate_behavioral_batch(5)
            print(f"Generated Q16-Q20: {len(questions_q16_q20)}")
            
            # Combine all
            all_questions_text = questions_q1_q5 + questions_q6_q15 + questions_q16_q20
            
            # Safety check: Ensure we have exactly 20 (or handle if AI returned fewer)
            # If AI returned more/less, slice or pad?
            # The generator guarantees 'count' items via fallback, so this should match.
            
            # 3. Save to DB
            question_objects = []
            
            for i, q_text in enumerate(all_questions_text):
                q_num = i + 1
                if q_num <= 15:
                    q_type = "technical"
                else:
                    q_type = "behavioral"
                    
                q = InterviewQuestion(
                    interview_id=interview.id,
                    question_number=q_num,
                    question_text=q_text,
                    question_type=q_type
                )
                db.add(q)
                question_objects.append(q)
            
            db.commit()
            print("Questions saved to DB")
            
        except Exception as e:
            print(f"Error generating questions: {e}")
            import traceback
            traceback.print_exc()
            # Fallback questions
            fallbacks = [
                "Tell me about yourself.",
                "Describe a challenging project you worked on.",
                "What refer technical skills do you have?",
                "How do you handle conflict in a team?",
                "Do you have any questions for us?"
            ]
            for i, q_text in enumerate(fallbacks):
                q = InterviewQuestion(
                    interview_id=interview.id,
                    question_number=i + 1,
                    question_text=q_text,
                    question_type="behavioral"
                )
                db.add(q)
            db.commit()
        
        return interview
    except Exception as e:
        print(f"CRITICAL ERROR in start_interview: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview: {str(e)}"
        )

@router.get("/{interview_id}/current-question", response_model=InterviewQuestionResponse)
async def get_current_question(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """Get current question for interview"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.candidate_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
        
    if interview.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Interview complete"
        )
    
    # Get latest unanswered question
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.question_number).all()
    
    # Find first unanswered question
    for question in questions:
        answers = db.query(InterviewAnswer).filter(
            InterviewAnswer.question_id == question.id
        ).all()
        if not answers:
            return question
            
    # If all questions are answered, check if we need to generate more?
    # For now, we assume fixed 5 questions as per legacy logic "generating questions once"
    # But if we wanted to support "infinite" or "upto 10", we would generate here.
    # Since we generated 5 at start, and legacy had 5 total, we stop here.
    
    # Interview complete
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Interview complete"
    )

@router.post("/{interview_id}/submit-answer")
async def submit_answer(
    interview_id: int,
    data: InterviewAnswerSubmit,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """Submit answer to current question"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.candidate_id == current_user.id,
        Interview.status == "in_progress"
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found or not in progress"
        )
    
    # Get current unanswered question
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.question_number).all()
    
    current_question = None
    if data.question_id:
        current_question = next((q for q in questions if q.id == data.question_id), None)
    else:
        for question in questions:
            answers = db.query(InterviewAnswer).filter(
                InterviewAnswer.question_id == question.id
            ).all()
            if not answers:
                current_question = question
                break
    
    if not current_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No unanswered question found or invalid question_id"
        )
    
    # Save answer
    answer = InterviewAnswer(
        question_id=current_question.id,
        answer_text=data.answer_text,
        submitted_at=datetime.utcnow()
    )
    
    db.add(answer)
    
    # Evaluate answer with AI
    try:
        job = interview.application.job
        evaluation = await evaluate_detailed_answer(
            question=current_question.question_text,
            answer=data.answer_text
        )
        
        answer.answer_score = float(evaluation.get("overall", 5))
        answer.skill_relevance_score = float(evaluation.get("technical_accuracy", 5))
        # Store full detailed evaluation JSON in the text field
        answer.answer_evaluation = json.dumps(evaluation)
        answer.evaluated_at = datetime.utcnow()
    except Exception as e:
        print(f"Error evaluating answer: {e}")
    
    db.commit()
    db.refresh(answer)
    
    return {"success": True, "answer_id": answer.id}

@router.post("/{interview_id}/end")
async def end_interview(
    interview_id: int,
    current_user: User = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """End interview and trigger evaluation"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.candidate_id == current_user.id,
        Interview.status == "in_progress"
    ).first()
    
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found or not in progress"
        )
    
    # End interview
    interview.status = "completed"
    interview.ended_at = datetime.utcnow()
    
    # Update application status
    interview.application.status = "interview_completed"
    
    # Calculate overall score
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).all()
    
    scores = []
    qa_pairs = []
    tech_scores = []
    for question in questions:
        answers = db.query(InterviewAnswer).filter(
            InterviewAnswer.question_id == question.id
        ).all()
        if answers:
            score = answers[0].answer_score
            tech_score = answers[0].skill_relevance_score
            if score is None:
                score = 5.0
            if tech_score is None:
                tech_score = 5.0
            scores.append(score)
            tech_scores.append(tech_score)
            qa_pairs.append({
                "question": question.question_text,
                "answer": answers[0].answer_text,
                "score": score
            })
        else:
            scores.append(0.0)
            tech_scores.append(0.0)
            qa_pairs.append({
                "question": question.question_text,
                "answer": "No answer provided.",
                "score": 0.0
            })
    
    overall_score = sum(scores) / len(scores) if scores else 5.0
    mean_technical_score = sum(tech_scores) / len(tech_scores) if tech_scores else 5.0
    interview.overall_score = overall_score
    interview.questions_asked = len(questions)
    
    db.commit()
    
    # Generate report
    try:
        job = interview.application.job
        report_data = await generate_interview_report(
            job_title=job.title,
            required_skills=job.required_skills,
            all_qa_pairs=qa_pairs,
            overall_score=overall_score
        )
        
        # Serialize detailed_feedback to JSON string if it's a dict/list
        detailed_feedback_val = report_data["detailed_feedback"]
        if isinstance(detailed_feedback_val, (dict, list)):
            detailed_feedback_val = json.dumps(detailed_feedback_val)
            
        report = InterviewReport(
            interview_id=interview_id,
            overall_score=report_data["overall_score"],
            technical_skills_score=mean_technical_score,
            communication_score=report_data["communication_score"],
            problem_solving_score=report_data["problem_solving_score"],
            strengths=report_data["strengths"],
            weaknesses=report_data["weaknesses"],
            summary=report_data["summary"],
            recommendation=report_data["recommendation"].lower().replace(" ", "_"),
            detailed_feedback=detailed_feedback_val
        )
        
        db.add(report)
        db.commit()

        # Send notification to HR
        from app.models import Notification
        try:
            notification = Notification(
                user_id=job.hr_id,
                notification_type="interview_completed",
                title=f"Interview Completed: {current_user.full_name}",
                message=f"{current_user.full_name} has completed the interview for {job.title}. AI Score: {overall_score:.1f}",
                related_application_id=interview.application_id,
                related_interview_id=interview_id
            )
            db.add(notification)
            db.commit()
        except Exception as e:
            print(f"Error creating notification: {e}")
            
        # ---------------------------------------------------------
        # integrate ReportManager for JSON file generation
        # ---------------------------------------------------------
        try:
            try:
                from backend.interview_process.report_manager import ReportManager
            except ImportError:
                from interview_process.report_manager import ReportManager
                
            report_manager = ReportManager()
            
            # Reconstruct session_state
            # 1. Candidate Info — read from stored analysis metadata
            meta = {}
            if interview.candidate_metadata:
                try:
                    meta = json.loads(interview.candidate_metadata)
                except Exception:
                    pass

            candidate_info = {
                "skills": meta.get("skills") or (str(interview.locked_skill).split(',') if interview.locked_skill else []),
                "primary_skill": interview.locked_skill or "general",
                "experience": meta.get("experience", "mid"),
                "confidence": meta.get("confidence", "N/A"),
                "communication": meta.get("communication", "N/A"),
                "intro_score": meta.get("intro_score", 0)
            }
            
            # 2. Responses
            responses_data = []
            for i, qa in enumerate(qa_pairs):
                # Try to parse the stored evaluation JSON
                eval_data = {}
                try:
                    # Find the answer object again or use what we have
                    # We have 'answer' text in qa_pairs, but we need the evaluation JSON
                    # which is in the Answer table. 
                    # Optimization: We already iterated answers above.
                    # Let's re-fetch or assume we need to query if we didn't keep it.
                    # Actually, let's just use what we have.
                    pass
                except:
                    pass
                    
                # Iterate questions again to get full data? 
                # Or just build from what we have. 
                # We need the `answer_evaluation` field from InterviewAnswer.
                
                # Let's find the specific answer object for this question
                ans_obj = db.query(InterviewAnswer).filter(
                     InterviewAnswer.question_id == questions[i].id
                ).first()
                
                evaluation_json = {}
                if ans_obj and ans_obj.answer_evaluation:
                    try:
                        evaluation_json = json.loads(ans_obj.answer_evaluation)
                    except:
                        pass
                
                responses_data.append({
                    "question": qa["question"],
                    "answer": qa["answer"],
                    "evaluation": evaluation_json,
                    "score": qa["score"],
                    "question_number": i + 1,
                    "question_type": questions[i].question_type
                })

            # 3. Questions Asked List
            questions_list = [q.question_text for q in questions]
            
            # 4. Messages (Simulated Transcript)
            messages = []
            messages.append({"role": "system", "content": f"Interview initialized for {job.title}", "timestamp": str(interview.started_at)})
            for resp in responses_data:
                messages.append({"role": "system", "content": f"Question: {resp['question']}"})
                messages.append({"role": "candidate", "content": resp['answer']})
            
            session_state = {
                "candidate_profile": candidate_info,
                "questions_asked": questions_list, # This is the list of strings
                "question_evaluations": responses_data, # This matches the report manager's expectation
                "questions": questions_list, # ReportManager uses this too
                "responses": responses_data, # InterviewManager uses this
                "overall_score": overall_score,
                "mean_technical_score": mean_technical_score,
                "final_score": overall_score,
                "messages": messages,
                "start_time": interview.started_at.timestamp() if interview.started_at else 0,
                "end_time": interview.ended_at.timestamp() if interview.ended_at else 0,
                "user_id": current_user.id # For ReportManager to link to DB if it wants (though we already did)
            }
            
            saved_path = report_manager.save_interview_report(session_state)
            print(f"✅ JSON Report saved to: {saved_path}")
            
        except Exception as e:
            print(f"❌ Error in ReportManager integration: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"Error generating report: {e}")
    
    return {"success": True, "interview_id": interview_id, "status": "completed"}

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
    
    # Check access
    if current_user.role == "candidate" and interview.candidate_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own interviews"
        )
    
    if current_user.role == "hr" and interview.application.job.hr_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view interviews for your jobs"
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
    
    return report
