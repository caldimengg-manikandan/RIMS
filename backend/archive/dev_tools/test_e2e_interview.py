from app.services.interview_agent.session_manager import SessionManager
from app.services.interview_agent.question_controller import QuestionController
from app.services.interview_agent.answer_processor import AnswerProcessor
from app.services.interview_agent.report_generator import ReportGenerator

def run_e2e_simulation():
    print("--- STARTING E2E RIMS INTERVIEW SIMULATION ---")
    
    # Mock DB Session
    db_session = None
    
    # Initialize Core Engines
    session_manager = SessionManager(db_session)
    question_controller = QuestionController(db_session)
    
    # 1. Start Session
    candidate_id = 101
    job_id = 99
    session = session_manager.start_interview_session(candidate_id, job_id)
    session_id = f"{candidate_id}_{job_id}_session"
    
    # Init Processors
    answer_processor = AnswerProcessor(db_session, session_id)
    report_generator = ReportGenerator(db_session, session_id)
    
    # 2. Ingest Context (RAG Pipeline happens inside ContextBuilder initialized by AnswerProcessor)
    print("\n[RAG] Ingesting Job Description and Resume...")
    answer_processor.context_builder.ingest_job_description(
        "We are looking for a Senior Python Backend Engineer.",
        ["Python", "FastAPI", "SQL", "System Design"]
    )
    answer_processor.context_builder.ingest_candidate_resume(
        "Senior Software Engineer with 5 years of Python experience, building highly scalable FastAPI backends."
    )
    
    evaluations = []
    
    # 3. Ask Question 1 (Medium - First Question)
    q1 = question_controller.select_first_question("Python")
    print(f"\n[AI Interviewer] {q1['text']}")
    
    a1 = "I use Python extensively, especially with FastAPI to build async REST APIs."
    print(f"[Candidate] {a1}")
    
    eval1 = answer_processor.process_answer(q1, a1)
    evaluations.append(eval1)
    print(f"[Scoring Engine] Initial Score: {eval1['technical_score']}")
    
    # 4. Generate Next Question based on eval1 score (Dynamic Difficulty Engine)
    q2 = question_controller.generate_next_question(session, eval1['technical_score'])
    print(f"\n[AI Interviewer] (Difficulty: {q2['difficulty']}) -> {q2['text']}")
    
    a2 = "I'm not exactly sure, but I think it has to do with variables."
    print(f"[Candidate] {a2}")
    
    # Mock worse evaluation for a2 to test difficulty drop
    eval2 = answer_processor.process_answer(q2, a2)
    # Simulate bad score
    eval2['technical_score'] = 4.0
    eval2['communication_score'] = 5.0
    eval2['correctness_score'] = 3.0
    evaluations.append(eval2)
    print(f"[Scoring Engine] Second Score: {eval2['technical_score']}")
    
    # 5. Generate Question 3 (Should drop difficulty to Easy)
    q3 = question_controller.generate_next_question(session, eval2['technical_score'])
    print(f"\n[AI Interviewer] (Difficulty: {q3['difficulty']}) -> {q3['text']}")
    
    a3 = "Yes, Python is a dynamically typed language."
    print(f"[Candidate] {a3}")
    
    eval3 = answer_processor.process_answer(q3, a3)
    evaluations.append(eval3)
    
    # 6. Generate Final Report
    print("\n--- GENERATING FINAL REPORT ---")
    final_report = report_generator.generate_final_report(evaluations)
    
    import json
    print(json.dumps(final_report, indent=4))
    
    print("\n--- E2E SIMULATION COMPLETE ---")

if __name__ == "__main__":
    run_e2e_simulation()
