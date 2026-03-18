-- HR Recruitment System - PostgreSQL Schema
-- Database: hr_system
-- Owner: postgres
-- Connection: postgresql+psycopg2://postgres:8765@localhost:5432/hr_system

-- ============================================================================
-- PART 1: USERS TABLE (Authentication & Roles)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('candidate', 'hr')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- PART 2: JOBS TABLE (HR creates job openings)
-- ============================================================================

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    required_skills TEXT NOT NULL, -- JSON array of skills or comma-separated
    experience_level VARCHAR(50) NOT NULL CHECK (experience_level IN ('junior', 'mid', 'senior')),
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'closed', 'on_hold')),
    hr_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hr_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_hr_id ON jobs(hr_id);

-- ============================================================================
-- PART 3: APPLICATIONS TABLE (Candidates apply for jobs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    resume_file_path VARCHAR(500),
    resume_file_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'submitted' CHECK (
        status IN ('submitted', 'approved_for_interview', 'rejected', 'hired', 'rejected_post_interview')
    ),
    hr_notes TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(job_id, candidate_id) -- Prevent duplicate applications to same job
);

CREATE INDEX idx_applications_candidate_id ON applications(candidate_id);
CREATE INDEX idx_applications_job_id ON applications(job_id);
CREATE INDEX idx_applications_status ON applications(status);

-- ============================================================================
-- PART 4: RESUME EXTRACTIONS (AI parsed resume data)
-- ============================================================================

CREATE TABLE IF NOT EXISTS resume_extractions (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL UNIQUE,
    extracted_text TEXT,
    extracted_skills TEXT, -- JSON array of extracted skills
    years_of_experience DECIMAL(5, 1),
    education TEXT, -- JSON array: [{"degree": "B.S.", "field": "CS", "university": "MIT"}]
    previous_roles TEXT, -- JSON array: [{"title": "Engineer", "company": "Google", "years": 3}]
    resume_score DECIMAL(3, 1) DEFAULT 0, -- Out of 10
    skill_match_percentage DECIMAL(5, 2) DEFAULT 0, -- Out of 100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE INDEX idx_resume_extractions_app_id ON resume_extractions(application_id);

-- ============================================================================
-- PART 5: INTERVIEWS TABLE (AI-driven interview sessions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL UNIQUE,
    status VARCHAR(50) DEFAULT 'not_started' CHECK (
        status IN ('not_started', 'in_progress', 'completed', 'cancelled')
    ),
    total_questions INTEGER DEFAULT 5,
    questions_asked INTEGER DEFAULT 0,
    overall_score DECIMAL(3, 1),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
);

CREATE INDEX idx_interviews_app_id ON interviews(application_id);
CREATE INDEX idx_interviews_status ON interviews(status);

-- ============================================================================
-- PART 6: INTERVIEW QUESTIONS (AI generated questions)
-- ============================================================================

CREATE TABLE IF NOT EXISTS interview_questions (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL,
    question_number INTEGER NOT NULL, -- 1, 2, 3, etc.
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) CHECK (question_type IN ('behavioral', 'technical', 'follow_up')),
    ai_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
);

CREATE INDEX idx_interview_questions_interview_id ON interview_questions(interview_id);

-- ============================================================================
-- PART 7: INTERVIEW ANSWERS (Candidate responses)
-- ============================================================================

CREATE TABLE IF NOT EXISTS interview_answers (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL,
    answer_text TEXT NOT NULL,
    answer_score DECIMAL(3, 1), -- 1-10
    answer_evaluation TEXT, -- AI evaluation of answer
    skill_relevance_score DECIMAL(3, 1), -- How well it matches the skill being assessed
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES interview_questions(id) ON DELETE CASCADE
);

CREATE INDEX idx_interview_answers_question_id ON interview_answers(question_id);

-- ============================================================================
-- PART 8: INTERVIEW REPORTS (AI generated comprehensive report)
-- ============================================================================

CREATE TABLE IF NOT EXISTS interview_reports (
    id SERIAL PRIMARY KEY,
    interview_id INTEGER NOT NULL UNIQUE,
    overall_score DECIMAL(3, 1),
    technical_skills_score DECIMAL(3, 1),
    communication_score DECIMAL(3, 1),
    problem_solving_score DECIMAL(3, 1),
    summary TEXT,
    strengths TEXT, -- JSON array or text
    weaknesses TEXT, -- JSON array or text
    recommendation VARCHAR(50) CHECK (recommendation IN ('recommended', 'consider', 'not_recommended')),
    detailed_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE
);

CREATE INDEX idx_interview_reports_interview_id ON interview_reports(interview_id);

-- ============================================================================
-- PART 9: HIRING DECISIONS (HR final decision on candidates)
-- ============================================================================

CREATE TABLE IF NOT EXISTS hiring_decisions (
    id SERIAL PRIMARY KEY,
    application_id INTEGER NOT NULL UNIQUE,
    hr_id INTEGER NOT NULL,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('hired', 'rejected')),
    decision_comments TEXT,
    decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
    FOREIGN KEY (hr_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_hiring_decisions_app_id ON hiring_decisions(application_id);
CREATE INDEX idx_hiring_decisions_hr_id ON hiring_decisions(hr_id);

-- ============================================================================
-- PART 10: NOTIFICATIONS (System notifications for users)
-- ============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    notification_type VARCHAR(50) NOT NULL, -- 'application_status', 'interview_invitation', 'decision', etc.
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    related_application_id INTEGER,
    related_interview_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_application_id) REFERENCES applications(id) ON DELETE SET NULL,
    FOREIGN KEY (related_interview_id) REFERENCES interviews(id) ON DELETE SET NULL
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- ============================================================================
-- PART 11: SESSION/ACTIVITY LOGS (Optional - for audit trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50), -- 'application', 'interview', 'job', etc.
    entity_id INTEGER,
    details TEXT, -- JSON
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at);

-- ============================================================================
-- PART 12: DATA INTEGRITY CHECKS & CONSTRAINTS
-- ============================================================================

-- Ensure application has resume before interview can be created
ALTER TABLE interviews ADD CONSTRAINT check_interview_requires_resume
    CHECK (application_id IN (
        SELECT id FROM applications WHERE resume_file_path IS NOT NULL
    ));

-- Ensure interview can only be created if application is approved
ALTER TABLE interviews ADD CONSTRAINT check_interview_approved_app
    CHECK (application_id IN (
        SELECT id FROM applications WHERE status = 'approved_for_interview'
    ));

-- ============================================================================
-- PART 13: SAMPLE DATA (For testing - OPTIONAL)
-- ============================================================================

-- Insert test HR user
INSERT INTO users (email, password_hash, full_name, role) 
VALUES ('hr@company.com', 'hashed_password_hr', 'HR Manager', 'hr')
ON CONFLICT (email) DO NOTHING;

-- Insert test candidate user
INSERT INTO users (email, password_hash, full_name, role) 
VALUES ('candidate@example.com', 'hashed_password_candidate', 'John Doe', 'candidate')
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- PART 14: VIEWS (For easier querying)
-- ============================================================================

-- View: Candidate applications with job and status details
CREATE OR REPLACE VIEW candidate_applications_view AS
SELECT 
    a.id as application_id,
    u.id as candidate_id,
    u.full_name as candidate_name,
    u.email as candidate_email,
    j.id as job_id,
    j.title as job_title,
    a.status,
    a.applied_at,
    re.resume_score,
    re.skill_match_percentage
FROM applications a
JOIN users u ON a.candidate_id = u.id
JOIN jobs j ON a.job_id = j.id
LEFT JOIN resume_extractions re ON a.id = re.application_id;

-- View: Interview pipeline with candidate and job info
CREATE OR REPLACE VIEW interview_pipeline_view AS
SELECT 
    i.id as interview_id,
    a.id as application_id,
    u.full_name as candidate_name,
    j.title as job_title,
    i.status as interview_status,
    i.started_at,
    ir.overall_score,
    ir.recommendation
FROM interviews i
JOIN applications a ON i.application_id = a.id
JOIN users u ON a.candidate_id = u.id
JOIN jobs j ON a.job_id = j.id
LEFT JOIN interview_reports ir ON i.id = ir.interview_id;

-- View: HR dashboard - all applicants with status
CREATE OR REPLACE VIEW hr_dashboard_view AS
SELECT 
    a.id as application_id,
    j.id as job_id,
    j.title as job_title,
    u.full_name as candidate_name,
    u.email as candidate_email,
    a.status as application_status,
    i.status as interview_status,
    ir.recommendation,
    hd.decision,
    a.applied_at
FROM applications a
JOIN jobs j ON a.job_id = j.id
JOIN users u ON a.candidate_id = u.id
LEFT JOIN interviews i ON a.id = i.application_id
LEFT JOIN interview_reports ir ON i.id = ir.interview_id
LEFT JOIN hiring_decisions hd ON a.id = hd.application_id;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Summary of tables created:
-- 1. users - User authentication & roles
-- 2. jobs - Job postings
-- 3. applications - Job applications
-- 4. resume_extractions - Parsed resume data
-- 5. interviews - Interview sessions
-- 6. interview_questions - AI-generated questions
-- 7. interview_answers - Candidate answers
-- 8. interview_reports - AI-generated reports
-- 9. hiring_decisions - Final hiring decisions
-- 10. notifications - User notifications
-- 11. activity_logs - Audit trail
--
-- Total: 11 tables + 3 views
-- Foreign keys enforced for data integrity
-- Indexes created for performance optimization
