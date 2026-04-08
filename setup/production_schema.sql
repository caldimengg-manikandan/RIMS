-- setup/production_schema.sql
-- Goal: 100% Symmetric with app.domain.models (Source of Truth)
-- Created: 2026-04-08

-- ============================================================================
-- 1. USERS & AUTH
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'candidate',
    is_active BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    approval_status VARCHAR(20) DEFAULT 'pending',
    otp_code VARCHAR(255),
    otp_expiry TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_users_role CHECK (role IN ('super_admin', 'hr', 'pending_hr', 'candidate')),
    CONSTRAINT check_users_approval_status CHECK (approval_status IN ('pending', 'approved', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================================
-- 2. JOBS
-- ============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50) UNIQUE,
    interview_token VARCHAR(50) UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    experience_level VARCHAR(50) NOT NULL,
    location VARCHAR(255) DEFAULT 'Remote',
    mode_of_work VARCHAR(50) DEFAULT 'Remote',
    job_type VARCHAR(50) DEFAULT 'Full-Time',
    domain VARCHAR(100) DEFAULT 'Engineering',
    status VARCHAR(50) DEFAULT 'open',
    primary_evaluated_skills TEXT,
    aptitude_enabled BOOLEAN DEFAULT FALSE,
    aptitude_mode VARCHAR(50) DEFAULT 'ai',
    first_level_enabled BOOLEAN DEFAULT FALSE,
    interview_mode VARCHAR(50),
    behavioral_role VARCHAR(50) DEFAULT 'general',
    uploaded_question_file VARCHAR(500),
    aptitude_config TEXT,
    aptitude_questions_file VARCHAR(500),
    duration_minutes INTEGER DEFAULT 60,
    hr_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    CONSTRAINT check_jobs_status CHECK (status IN ('open', 'closed', 'on_hold'))
);

-- ============================================================================
-- 3. APPLICATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    hr_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    candidate_name VARCHAR(255) NOT NULL,
    candidate_email VARCHAR(255),
    candidate_phone TEXT,
    candidate_phone_hash VARCHAR(64),
    candidate_phone_normalized VARCHAR(50),
    candidate_phone_raw TEXT,
    resume_file_path VARCHAR(500),
    resume_file_name VARCHAR(255),
    candidate_photo_path VARCHAR(500),
    status VARCHAR(50) DEFAULT 'applied',
    resume_status VARCHAR(32) DEFAULT 'pending',
    hr_notes TEXT,
    resume_score FLOAT DEFAULT 0,
    aptitude_score FLOAT DEFAULT 0,
    interview_score FLOAT DEFAULT 0,
    composite_score FLOAT DEFAULT 0,
    recommendation VARCHAR(50),
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parsing_started_at TIMESTAMP,
    file_status VARCHAR(20) DEFAULT 'active',
    retry_count INTEGER DEFAULT 0,
    failure_reason VARCHAR(1000),
    last_attempt_at TIMESTAMP,
    background_task_id VARCHAR(100),
    scoring_metadata TEXT,
    
    -- Onboarding
    offer_sent BOOLEAN DEFAULT FALSE,
    offer_sent_date TIMESTAMP,
    joining_date TIMESTAMP,
    offer_approval_status VARCHAR(20) DEFAULT 'pending',
    offer_approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    offer_approved_at TIMESTAMP,
    offer_response_status VARCHAR(20) DEFAULT 'pending',
    offer_response_date TIMESTAMP,
    offer_token VARCHAR(100) UNIQUE,
    offer_short_id VARCHAR(20) UNIQUE,
    offer_token_expiry TIMESTAMP WITH TIME ZONE,
    offer_token_used BOOLEAN DEFAULT FALSE,
    offer_template_snapshot TEXT,
    offer_pdf_path VARCHAR(500),
    offer_accepted_ip VARCHAR(50),
    offer_accepted_user_agent TEXT,
    offer_email_status VARCHAR(20) DEFAULT 'pending',
    offer_email_retry_count INTEGER DEFAULT 0,
    reminder_sent_at TIMESTAMP,

    -- ID Card
    employee_id VARCHAR(50) UNIQUE,
    id_card_url VARCHAR(500),
    onboarded_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_application_job_email UNIQUE (job_id, candidate_email),
    CONSTRAINT uq_application_job_phone_hash UNIQUE (job_id, candidate_phone_hash),
    CONSTRAINT check_applications_status CHECK (status IN ('applied', 'screened', 'aptitude_round', 'ai_interview', 'interview_scheduled', 'interview_completed', 'hired', 'pending_approval', 'offer_sent', 'accepted', 'rejected', 'onboarded', 'physical_interview', 'review_later'))
);

-- ============================================================================
-- 4. PIPELINE STAGES
-- ============================================================================
CREATE TABLE IF NOT EXISTS application_stages (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    stage_name VARCHAR(100) NOT NULL,
    stage_status VARCHAR(50) DEFAULT 'pending',
    score FLOAT,
    evaluation_notes TEXT,
    evaluator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 5. RESUME EXTRACTIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS resume_extractions (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL UNIQUE REFERENCES applications(id) ON DELETE CASCADE,
    extracted_text TEXT,
    summary TEXT,
    extracted_skills TEXT,
    years_of_experience FLOAT,
    education TEXT,
    previous_roles TEXT,
    experience_level VARCHAR(50),
    resume_score FLOAT DEFAULT 0,
    skill_match_percentage FLOAT DEFAULT 0,
    candidate_name VARCHAR(255),
    email VARCHAR(255),
    phone_number VARCHAR(50),
    reasoning JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 6. INTERVIEWS
-- ============================================================================
CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    test_id VARCHAR(50) UNIQUE,
    application_id INTEGER NOT NULL UNIQUE REFERENCES applications(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'not_started',
    locked_skill VARCHAR(50),
    total_questions INTEGER DEFAULT 20,
    questions_asked INTEGER DEFAULT 0,
    current_difficulty VARCHAR(20) DEFAULT 'medium',
    overall_score FLOAT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    access_key_hash VARCHAR(255),
    expires_at TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    interview_stage VARCHAR(50) DEFAULT 'first_level',
    aptitude_score FLOAT,
    aptitude_completed_at TIMESTAMP,
    duration_minutes INTEGER DEFAULT 60,
    aptitude_completed BOOLEAN DEFAULT FALSE,
    first_level_completed BOOLEAN DEFAULT FALSE,
    first_level_score FLOAT,
    video_recording_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 7. QUESTIONS & ANSWERS
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_questions (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),
    options TEXT,
    correct_answer TEXT,
    ai_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interview_answers (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL UNIQUE REFERENCES interview_questions(id) ON DELETE CASCADE,
    interview_id INTEGER REFERENCES interviews(id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    answer_score FLOAT,
    answer_evaluation TEXT,
    skill_relevance_score FLOAT,
    technical_score FLOAT,
    completeness_score FLOAT,
    clarity_score FLOAT,
    depth_score FLOAT,
    practicality_score FLOAT,
    ai_used BOOLEAN DEFAULT FALSE,
    fallback_used BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    reasoning JSONB,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP
);

-- ============================================================================
-- 8. REPORTS & DECISIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_reports (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL UNIQUE REFERENCES interviews(id) ON DELETE CASCADE,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    overall_score FLOAT,
    technical_skills_score FLOAT,
    communication_score FLOAT,
    problem_solving_score FLOAT,
    candidate_name VARCHAR(255),
    candidate_email VARCHAR(255),
    applied_role VARCHAR(255),
    summary TEXT,
    strengths TEXT,
    weaknesses TEXT,
    recommendation VARCHAR(50),
    detailed_feedback TEXT,
    aptitude_score FLOAT,
    behavioral_score FLOAT,
    combined_score FLOAT,
    evaluated_skills TEXT,
    termination_reason VARCHAR(255),
    ai_used BOOLEAN DEFAULT FALSE,
    fallback_used BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    reasoning JSONB,
    retry_count INTEGER DEFAULT 0,
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hiring_decisions (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL UNIQUE REFERENCES applications(id) ON DELETE CASCADE,
    hr_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    decision VARCHAR(20) NOT NULL,
    decision_comments TEXT,
    joining_date TIMESTAMP,
    offer_letter_path VARCHAR(500),
    decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_hiring_decision CHECK (decision IN ('hired', 'rejected'))
);

-- ============================================================================
-- 9. SESSIONS & EVENTS (ADAPTIVE ENGINE)
-- ============================================================================
CREATE TABLE IF NOT EXISTS interview_sessions (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    final_score FLOAT,
    difficulty_level VARCHAR(50) DEFAULT 'medium'
);

CREATE TABLE IF NOT EXISTS interview_events (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    payload TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 10. EVALUATION ENGINE & BANK
-- ============================================================================
CREATE TABLE IF NOT EXISTS ai_evaluations (
    id SERIAL PRIMARY KEY,
    answer_id INTEGER NOT NULL REFERENCES interview_answers(id) ON DELETE CASCADE,
    technical_score FLOAT,
    communication_score FLOAT,
    reasoning_score FLOAT,
    feedback_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS question_bank (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(100),
    role VARCHAR(100),
    difficulty VARCHAR(50),
    question_text TEXT NOT NULL,
    expected_key_points TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidate_skills (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    skill_name VARCHAR(100) NOT NULL,
    proficiency_score FLOAT,
    years_experience FLOAT
);

-- ============================================================================
-- 11. VERSIONING
-- ============================================================================
CREATE TABLE IF NOT EXISTS job_versions (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    primary_evaluated_skills TEXT,
    experience_level VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, version_number)
);

CREATE TABLE IF NOT EXISTS resume_extraction_versions (
    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    extracted_text TEXT,
    extracted_skills TEXT,
    resume_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(application_id, version_number)
);

CREATE TABLE IF NOT EXISTS interview_report_versions (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER REFERENCES interviews(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    overall_score FLOAT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(interview_id, version_number)
);

-- ============================================================================
-- 12. UTILITY & AUDIT
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INTEGER,
    details TEXT,
    ip_address VARCHAR(50),
    is_critical BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    related_application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    related_interview_id INTEGER REFERENCES interviews(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS global_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
