import datetime
from datetime import timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, UniqueConstraint, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.infrastructure.database import Base
from app.core.encryption import EncryptedText


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'hr_manager', 'recruiter', 'interviewer', 'candidate', 'hr')", name='check_users_role'),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, index=True)  # 'admin', 'hr_manager', 'recruiter', 'interviewer', 'candidate'
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String(255), nullable=True)
    otp_expiry = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    # Relationships
    jobs = relationship("Job", back_populates="hr")
    hiring_decisions = relationship("HiringDecision", back_populates="hr")
    notifications = relationship("Notification", back_populates="user")
    stages_handled = relationship("ApplicationStage", back_populates="evaluator")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'closed', 'on_hold')", name='check_jobs_status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, index=True, nullable=True)
    interview_token = Column(String(50), unique=True, index=True, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    experience_level = Column(String(50), nullable=False)
    location = Column(String(255), default='Remote')
    mode_of_work = Column(String(50), default='Remote')
    job_type = Column(String(50), default='Full-Time')
    domain = Column(String(100), default='Engineering')
    status = Column(String(50), default='open', index=True)
    primary_evaluated_skills = Column(Text)
    aptitude_enabled = Column(Boolean, default=False)
    aptitude_mode = Column(String(50), default='ai')
    first_level_enabled = Column(Boolean, default=False)
    interview_mode = Column(String(50), nullable=True)
    behavioral_role = Column(String(50), default='general')
    uploaded_question_file = Column(String(500), nullable=True)
    aptitude_config = Column(Text, nullable=True)
    aptitude_questions_file = Column(String(500), nullable=True)
    hr_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    hr = relationship("User", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('applied', 'aptitude_round', 'ai_interview', 'ai_interview_completed', "
            "'review_later', 'physical_interview', 'hired', 'rejected')",
            name='check_applications_status'
        ),
        UniqueConstraint('job_id', 'candidate_email', name='uq_application_job_email'),
        Index('ix_applications_job_status', 'job_id', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False, index=True)
    candidate_name = Column(String(255), nullable=False)
    candidate_email = Column(String(255), nullable=False, index=True)
    candidate_phone = Column(EncryptedText)
    resume_file_path = Column(String(500))
    resume_file_name = Column(String(255))
    candidate_photo_path = Column(String(500), nullable=True)
    status = Column(String(50), default='applied', index=True)
    hr_notes = Column(EncryptedText)
    
    # Composite Scores (Point 2)
    resume_score = Column(Float, default=0)
    aptitude_score = Column(Float, default=0)
    interview_score = Column(Float, default=0)
    composite_score = Column(Float, default=0, index=True)
    
    # Recommendations (Point 4)
    recommendation = Column(String(50)) # 'Strong Hire', 'Hire', 'Borderline', 'Reject'
    
    applied_at = Column(DateTime, default=func.now(), server_default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    # Relationships
    job = relationship("Job", back_populates="applications")
    resume_extraction = relationship("ResumeExtraction", back_populates="application", uselist=False, cascade="all, delete-orphan")
    interview = relationship("Interview", back_populates="application", uselist=False, cascade="all, delete-orphan")
    hiring_decision = relationship("HiringDecision", back_populates="application", uselist=False, cascade="all, delete-orphan")
    pipeline_stages = relationship("ApplicationStage", back_populates="application", cascade="all, delete-orphan")
    notifications = relationship("Notification", foreign_keys="[Notification.related_application_id]", cascade="all, delete-orphan")
    candidate_skills = relationship("CandidateSkill", cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", cascade="all, delete-orphan")  # Legacy — kept for migration safety


class ApplicationStage(Base):
    __tablename__ = "application_stages"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    stage_name = Column(String(100), nullable=False) # e.g., 'Aptitude Round'
    stage_status = Column(String(50), default='pending') # 'pending', 'pass', 'fail', 'hold'
    score = Column(Float, nullable=True)
    evaluation_notes = Column(EncryptedText)
    evaluator_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())

    # Relationships
    application = relationship("Application", back_populates="pipeline_stages")
    evaluator = relationship("User", back_populates="stages_handled")


class ResumeExtraction(Base):
    __tablename__ = "resume_extractions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, unique=True, index=True)
    extracted_text = Column(EncryptedText)
    summary = Column(Text)  # Added summary field
    extracted_skills = Column(Text)  # JSON array
    years_of_experience = Column(Float)
    education = Column(Text)  # JSON array
    previous_roles = Column(Text)  # JSON array
    experience_level = Column(String(50))  # 'Intern', 'Junior', 'Mid-Level', 'Senior', 'Lead'
    resume_score = Column(Float, default=0)  # Out of 10
    skill_match_percentage = Column(Float, default=0)  # Out of 100
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())


    # Relationships
    application = relationship("Application", back_populates="resume_extraction")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(String(50), unique=True, index=True, nullable=True)  # New Test ID field
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, unique=True, index=True)
    status = Column(String(50), default='not_started', index=True)  # 'not_started', 'in_progress', 'completed', 'cancelled'
    locked_skill = Column(String(50))  # e.g. 'backend', 'frontend'
    total_questions = Column(Integer, default=20)
    questions_asked = Column(Integer, default=0)
    overall_score = Column(Float)
    started_at = Column(DateTime, index=True)
    ended_at = Column(DateTime, index=True)
    access_key_hash = Column(String(255))
    expires_at = Column(DateTime)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    interview_stage = Column(String(50), default='first_level')  # 'aptitude', 'first_level'
    aptitude_score = Column(Float, nullable=True)
    aptitude_completed_at = Column(DateTime, nullable=True)
    aptitude_completed = Column(Boolean, default=False)
    first_level_completed = Column(Boolean, default=False)
    first_level_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())


    # Relationships
    application = relationship("Application", back_populates="interview")
    questions = relationship(
        "InterviewQuestion",
        back_populates="interview",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    report = relationship(
        "InterviewReport",
        back_populates="interview",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    issues = relationship("InterviewIssue", back_populates="interview", cascade="all, delete-orphan")
    feedback = relationship("InterviewFeedback", back_populates="interview", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False, index=True)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50))  # 'aptitude', 'behavioral', 'technical', 'follow_up'
    options = Column(Text, nullable=True)  # JSON array for multiple choice options
    question_options = Column(Text, nullable=True)  # JSON array for MCQ options (aptitude)
    correct_answer = Column(Text, nullable=True)
    correct_option = Column(Integer, nullable=True)  # Index of correct MCQ option
    ai_generated_at = Column(DateTime, default=datetime.datetime.now(timezone.utc))
    created_at = Column(DateTime, default=datetime.datetime.now(timezone.utc))
    
    # Relationships
    interview = relationship("Interview", back_populates="questions")
    answers = relationship("InterviewAnswer", back_populates="question")


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    __table_args__ = (
        UniqueConstraint('question_id', name='uq_answer_per_question'),
    )

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey('interview_questions.id'), nullable=False, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), index=True, nullable=True)
    answer_text = Column(EncryptedText, nullable=False)
    answer_score = Column(Float)  # 1-10
    answer_evaluation = Column(EncryptedText)  # AI evaluation
    skill_relevance_score = Column(Float)
    technical_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    clarity_score = Column(Float, nullable=True)
    depth_score = Column(Float, nullable=True)
    practicality_score = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=func.now(), server_default=func.now())
    evaluated_at = Column(DateTime)

    # Relationships
    question = relationship("InterviewQuestion", back_populates="answers")
    interview = relationship("Interview")


class InterviewReport(Base):
    __tablename__ = "interview_reports"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False, unique=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True, index=True)
    overall_score = Column(Float)
    technical_skills_score = Column(Float)
    communication_score = Column(Float)
    problem_solving_score = Column(Float)
    candidate_name = Column(String(255))
    candidate_email = Column(String(255))
    applied_role = Column(String(255))
    summary = Column(EncryptedText)
    strengths = Column(EncryptedText)  # JSON array or text
    weaknesses = Column(EncryptedText)  # JSON array or text
    recommendation = Column(String(50))  # 'recommended', 'consider', 'not_recommended'
    detailed_feedback = Column(EncryptedText)
    aptitude_score = Column(Float, nullable=True)
    behavioral_score = Column(Float, nullable=True)
    combined_score = Column(Float, nullable=True)
    evaluated_skills = Column(Text)  # JSON array of evaluated skills
    termination_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    # Relationships
    interview = relationship("Interview", back_populates="report")


class HiringDecision(Base):
    __tablename__ = "hiring_decisions"
    __table_args__ = (
        CheckConstraint("decision IN ('hired', 'rejected')", name='check_hiring_decision'),
    )

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, unique=True, index=True)
    hr_id = Column(Integer, ForeignKey('users.id'), index=True)
    decision = Column(String(20), nullable=False)  # 'hired', 'rejected'
    decision_comments = Column(EncryptedText)
    decided_at = Column(DateTime, default=func.now(), server_default=func.now())
    created_at = Column(DateTime, default=func.now(), server_default=func.now())

    # Relationships
    application = relationship("Application", back_populates="hiring_decision")
    hr = relationship("User", back_populates="hiring_decisions")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(EncryptedText, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    related_application_id = Column(Integer, ForeignKey('applications.id'))
    related_interview_id = Column(Integer, ForeignKey('interviews.id'))
    created_at = Column(DateTime, default=func.now(), server_default=func.now(), index=True)
    read_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="notifications")



class InterviewIssue(Base):
    __tablename__ = "interview_issues"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'resolved', 'dismissed')", name='check_issue_status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False, index=True)
    candidate_name = Column(String(255))
    candidate_email = Column(String(255))
    issue_type = Column(String(100))  # 'interruption', 'technical', 'misconduct_appeal'
    description = Column(Text, nullable=False)
    status = Column(String(20), default='pending', index=True)
    hr_response = Column(Text)
    is_reissue_granted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    resolved_at = Column(DateTime)

    # Relationships
    interview = relationship("Interview", back_populates="issues")


class InterviewFeedback(Base):
    __tablename__ = "interview_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False, unique=True, index=True)
    ui_ux_rating = Column(Integer)  # 1-5
    feedback_text = Column(Text)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())

    # Relationships
    interview = relationship("Interview", back_populates="feedback")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    action = Column(String(255), nullable=False) # e.g., 'RESUME_SCREENING_COMPLETED'
    resource_type = Column(String(100)) # e.g., 'Application'
    resource_id = Column(Integer)
    details = Column(EncryptedText) 
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=func.now(), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default='pending', index=True)  # 'pending', 'active', 'completed', 'aborted'
    final_score = Column(Float, nullable=True)
    difficulty_level = Column(String(50), default='medium')

    # Relationships
    application = relationship("Application", back_populates="interview_sessions")

    # Relationships
    events = relationship("InterviewEvent", back_populates="session", cascade="all, delete-orphan")


class InterviewEvent(Base):
    __tablename__ = "interview_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('interview_sessions.id'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # 'question_asked', 'answer_received', 'ai_evaluated', 'status_changed'
    payload = Column(Text, nullable=True)  # JSON serialized data
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Relationships
    session = relationship("InterviewSession", back_populates="events")


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(100), index=True)  # e.g. 'Engineering', 'Sales'
    role = Column(String(100), index=True)    # e.g. 'Frontend', 'Backend'
    difficulty = Column(String(50), index=True) # 'easy', 'medium', 'hard'
    question_text = Column(Text, nullable=False)
    expected_key_points = Column(Text) # JSON array of points
    created_at = Column(DateTime(timezone=True), default=func.now())


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    skill_name = Column(String(100), nullable=False, index=True)
    proficiency_score = Column(Float, nullable=True) # 0-10 based on AI analysis
    years_experience = Column(Float, nullable=True)

    # Relationships
    application = relationship("Application", back_populates="candidate_skills")


class AIEvaluation(Base):
    __tablename__ = "ai_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey('interview_answers.id'), nullable=False, index=True)
    technical_score = Column(Float)
    communication_score = Column(Float)
    reasoning_score = Column(Float)
    feedback_text = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
