from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# ============================================================================
# Auth Schemas
# ============================================================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# Job Schemas
# ============================================================================

class JobCreate(BaseModel):
    title: str
    description: str
    experience_level: str  # 'junior', 'mid', 'senior'
    location: Optional[str] = None
    mode_of_work: Optional[str] = 'Remote'
    job_type: Optional[str] = 'Full-Time'
    domain: Optional[str] = 'Engineering'
    primary_evaluated_skills: Optional[List[str]] = None
    # Interview Config overrides
    aptitude_enabled: Optional[bool] = False
    aptitude_mode: Optional[str] = "ai"
    first_level_enabled: Optional[bool] = False
    interview_mode: Optional[str] = None
    behavioral_role: Optional[str] = "general"
    interview_token: Optional[str] = None
    uploaded_question_file: Optional[str] = None
    aptitude_questions_file: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    experience_level: Optional[str] = None
    location: Optional[str] = None
    mode_of_work: Optional[str] = None
    job_type: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[str] = None  # 'open', 'closed', 'on_hold'
    primary_evaluated_skills: Optional[List[str]] = None
    # Interview pipeline config
    aptitude_enabled: Optional[bool] = None
    first_level_enabled: Optional[bool] = None
    interview_mode: Optional[str] = None
    uploaded_question_file: Optional[str] = None
    aptitude_config: Optional[dict] = None
    aptitude_questions_file: Optional[str] = None

class JobResponse(BaseModel):
    id: int
    job_id: Optional[str] = None
    title: str
    description: str
    experience_level: str
    location: Optional[str]
    mode_of_work: Optional[str] = 'Remote'
    job_type: Optional[str]
    domain: Optional[str]
    status: str
    closed_at: Optional[datetime] = None
    primary_evaluated_skills: Optional[str] = None
    # Interview pipeline config
    # Interview pipeline config
    aptitude_enabled: Optional[bool] = False
    aptitude_mode: Optional[str] = "ai"
    first_level_enabled: Optional[bool] = False
    interview_mode: Optional[str] = None
    behavioral_role: Optional[str] = "general"
    interview_token: Optional[str] = None
    uploaded_question_file: Optional[str] = None
    aptitude_config: Optional[str] = None
    aptitude_questions_file: Optional[str] = None
    is_applied: bool = False
    hr_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class JobExtractionResponse(BaseModel):
    title: str = ""
    experience_level: str = ""
    domain: str = ""
    job_type: str = ""
    location: str = ""
    description: str = ""
    primary_evaluated_skills: List[str] = []

# ============================================================================
# Application Schemas
# ============================================================================

class ApplicationCreate(BaseModel):
    job_id: int

class ApplicationStatusUpdate(BaseModel):
    status: str  # 'approved_for_interview', 'rejected'
    hr_notes: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    candidate_name: str
    candidate_email: str
    candidate_phone: Optional[str] = None
    resume_file_name: Optional[str]
    resume_file_path: Optional[str]
    candidate_photo_path: Optional[str] = None
    status: str
    hr_notes: Optional[str] = None
    
    # Enterprise Scoring (Point 2)
    resume_score: Optional[float] = 0
    aptitude_score: Optional[float] = 0
    interview_score: Optional[float] = 0
    composite_score: Optional[float] = 0
    recommendation: Optional[str] = None
    
    applied_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ApplicationStageResponse(BaseModel):
    id: int
    stage_name: str
    stage_status: str
    score: Optional[float] = None
    evaluation_notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ApplicationDetailResponse(ApplicationResponse):
    job: JobResponse
    resume_extraction: Optional['ResumeExtractionResponse'] = None
    interview: Optional['InterviewResponse'] = None
    pipeline_stages: List[ApplicationStageResponse] = []

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# Resume Schemas
# ============================================================================

class ResumeExtractionResponse(BaseModel):
    id: int
    application_id: int
    extracted_text: Optional[str]  # Full text
    summary: Optional[str]  # AI summary
    extracted_skills: Optional[str]
    years_of_experience: Optional[float]
    education: Optional[str]
    previous_roles: Optional[str]
    experience_level: Optional[str]
    resume_score: float
    skill_match_percentage: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# Interview Report Schemas
# ============================================================================

class InterviewReportResponse(BaseModel):
    id: int
    interview_id: int
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    applied_role: Optional[str]
    overall_score: Optional[float]
    technical_skills_score: Optional[float]
    communication_score: Optional[float]
    problem_solving_score: Optional[float]
    summary: Optional[str]
    strengths: Optional[str]
    weaknesses: Optional[str]
    recommendation: Optional[str]
    detailed_feedback: Optional[str]
    aptitude_score: Optional[float] = None
    behavioral_score: Optional[float] = None
    combined_score: Optional[float] = None
    evaluated_skills: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# Interview Schemas
# ============================================================================

class InterviewStart(BaseModel):
    application_id: int

class InterviewAccess(BaseModel):
    email: str
    access_key: str

class InterviewAnswerSubmit(BaseModel):
    question_id: int
    answer_text: str

class InterviewQuestionResponse(BaseModel):
    id: int
    interview_id: int
    question_number: int
    question_text: str
    question_type: Optional[str]
    options: Optional[str] = None
    
    class Config:
        from_attributes = True

class InterviewAnswerResponse(BaseModel):
    id: int
    question_id: int
    answer_text: str
    answer_score: Optional[float]
    answer_evaluation: Optional[str]
    skill_relevance_score: Optional[float]
    submitted_at: datetime
    
    class Config:
        from_attributes = True

class InterviewListResponse(BaseModel):
    id: int
    test_id: Optional[str] = None
    status: str
    created_at: datetime
    job_id: int
    job_title: str
    locked_skill: Optional[str]
    score: Optional[float]
    
    class Config:
        from_attributes = True

class InterviewResponse(BaseModel):
    id: int
    test_id: Optional[str] = None
    application_id: int
    status: str
    locked_skill: Optional[str] = None
    total_questions: int
    questions_asked: int
    overall_score: Optional[float]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    # Sequential pipeline fields
    interview_stage: Optional[str] = 'first_level'
    aptitude_score: Optional[float] = None
    aptitude_completed_at: Optional[datetime] = None
    report: Optional[InterviewReportResponse] = None
    
    class Config:
        from_attributes = True

class InterviewDetailResponse(InterviewResponse):
    questions: List[InterviewQuestionResponse] = []

# ============================================================================
# Hiring Decision Schemas
# ============================================================================

class HiringDecisionMake(BaseModel):
    decision: str  # 'hired' or 'rejected'
    decision_comments: Optional[str] = None

class HiringDecisionResponse(BaseModel):
    id: int
    application_id: int
    decision: str
    decision_comments: Optional[str]
    decided_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================================
# Notification Schemas
# ============================================================================

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    related_application_id: Optional[int] = None
    created_at: datetime
    read_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============================================================================
# Ticket / Support Schemas
# ============================================================================

class InterviewIssueCreate(BaseModel):
    interview_id: int
    issue_type: str  # 'interruption', 'technical', 'misconduct_appeal'
    description: str

class GeneralGrievanceCreate(BaseModel):
    email: EmailStr
    access_key: str
    issue_type: str
    description: str

class InterviewIssueResolve(BaseModel):
    hr_response: str
    action: str  # 'reissue_key', 'dismiss', 'resolve'
    send_email: bool = True

class InterviewIssueResponse(BaseModel):
    id: int
    interview_id: int
    application_id: Optional[int] = None
    test_id: Optional[str] = None
    job_id: Optional[int] = None
    job_identifier: Optional[str] = None
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    issue_type: str
    description: str
    status: str
    hr_response: Optional[str]
    is_reissue_granted: bool
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

class InterviewFeedbackCreate(BaseModel):
    interview_id: int
    ui_ux_rating: int
    feedback_text: Optional[str] = None

class InterviewFeedbackResponse(BaseModel):
    id: int
    interview_id: int
    ui_ux_rating: int
    feedback_text: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserVerifyOTP(BaseModel):
    email: EmailStr
    otp: str
