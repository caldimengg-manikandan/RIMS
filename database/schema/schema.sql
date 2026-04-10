-- RIMs Database Schema (PostgreSQL)
-- Generated from SQLAlchemy models


CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	is_active BOOLEAN, 
	is_verified BOOLEAN, 
	approval_status VARCHAR(20), 
	otp_code VARCHAR(255), 
	otp_expiry TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT check_users_role CHECK (role IN ('super_admin', 'hr', 'pending_hr', 'candidate')), 
	CONSTRAINT check_users_approval_status CHECK (approval_status IN ('pending', 'approved', 'rejected'))
)


CREATE INDEX ix_users_id ON users (id)
CREATE INDEX ix_users_otp_expiry ON users (otp_expiry)
CREATE UNIQUE INDEX ix_users_email ON users (email)
CREATE INDEX ix_users_approval_status ON users (approval_status)
CREATE INDEX ix_users_role ON users (role)

CREATE TABLE question_bank (
	id SERIAL NOT NULL, 
	domain VARCHAR(100), 
	role VARCHAR(100), 
	difficulty VARCHAR(50), 
	question_text TEXT NOT NULL, 
	expected_key_points TEXT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)


CREATE INDEX ix_question_bank_id ON question_bank (id)
CREATE INDEX ix_question_bank_domain ON question_bank (domain)
CREATE INDEX ix_question_bank_role ON question_bank (role)
CREATE INDEX ix_question_bank_difficulty ON question_bank (difficulty)

CREATE TABLE global_settings (
	id SERIAL NOT NULL, 
	key VARCHAR(100) NOT NULL, 
	value TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)


CREATE UNIQUE INDEX ix_global_settings_key ON global_settings (key)
CREATE INDEX ix_global_settings_id ON global_settings (id)

CREATE TABLE jobs (
	id SERIAL NOT NULL, 
	job_id VARCHAR(50), 
	interview_token VARCHAR(50), 
	title VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	experience_level VARCHAR(50) NOT NULL, 
	location VARCHAR(255), 
	mode_of_work VARCHAR(50), 
	job_type VARCHAR(50), 
	domain VARCHAR(100), 
	status VARCHAR(50), 
	primary_evaluated_skills TEXT, 
	aptitude_enabled BOOLEAN, 
	aptitude_mode VARCHAR(50), 
	first_level_enabled BOOLEAN, 
	interview_mode VARCHAR(50), 
	behavioral_role VARCHAR(50), 
	uploaded_question_file VARCHAR(500), 
	aptitude_config TEXT, 
	aptitude_questions_file VARCHAR(500), 
	duration_minutes INTEGER, 
	hr_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	closed_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT check_jobs_status CHECK (status IN ('open', 'closed', 'on_hold')), 
	FOREIGN KEY(hr_id) REFERENCES users (id) ON DELETE CASCADE
)


CREATE INDEX ix_jobs_location ON jobs (location)
CREATE INDEX ix_jobs_primary_evaluated_skills ON jobs (primary_evaluated_skills)
CREATE INDEX ix_jobs_description ON jobs (description)
CREATE INDEX ix_jobs_experience_level ON jobs (experience_level)
CREATE UNIQUE INDEX ix_jobs_interview_token ON jobs (interview_token)
CREATE UNIQUE INDEX ix_jobs_job_id ON jobs (job_id)
CREATE INDEX ix_jobs_hr_id ON jobs (hr_id)
CREATE INDEX ix_jobs_status ON jobs (status)
CREATE INDEX ix_jobs_id ON jobs (id)
CREATE INDEX ix_jobs_domain ON jobs (domain)
CREATE INDEX ix_jobs_title ON jobs (title)

CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(255) NOT NULL, 
	resource_type VARCHAR(100), 
	resource_id INTEGER, 
	details TEXT, 
	ip_address VARCHAR(50), 
	is_critical BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)


CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id)
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at)
CREATE INDEX ix_audit_logs_id ON audit_logs (id)

CREATE TABLE applications (
	id SERIAL NOT NULL, 
	job_id INTEGER NOT NULL, 
	hr_id INTEGER, 
	candidate_name VARCHAR(255) NOT NULL, 
	candidate_email VARCHAR(255), 
	candidate_phone TEXT, 
	candidate_phone_hash VARCHAR(64), 
	candidate_phone_normalized VARCHAR(50), 
	candidate_phone_raw TEXT, 
	resume_file_path VARCHAR(500), 
	resume_file_name VARCHAR(255), 
	candidate_photo_path VARCHAR(500), 
	status VARCHAR(50), 
	resume_status VARCHAR(32), 
	hr_notes TEXT, 
	resume_score FLOAT, 
	aptitude_score FLOAT, 
	interview_score FLOAT, 
	composite_score FLOAT, 
	recommendation VARCHAR(50), 
	applied_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	parsing_started_at TIMESTAMP WITHOUT TIME ZONE, 
	file_status VARCHAR(20), 
	retry_count INTEGER, 
	failure_reason VARCHAR(1000), 
	last_attempt_at TIMESTAMP WITHOUT TIME ZONE, 
	background_task_id VARCHAR(100), 
	scoring_metadata TEXT, 
	offer_sent BOOLEAN, 
	offer_sent_date TIMESTAMP WITHOUT TIME ZONE, 
	joining_date TIMESTAMP WITHOUT TIME ZONE, 
	onboarding_approval_status VARCHAR(20), 
	offer_approval_status VARCHAR(20), 
	offer_approved_by INTEGER, 
	offer_approved_at TIMESTAMP WITHOUT TIME ZONE, 
	offer_response_status VARCHAR(20), 
	offer_response_date TIMESTAMP WITHOUT TIME ZONE, 
	offer_token VARCHAR(100), 
	offer_short_id VARCHAR(20), 
	offer_token_expiry TIMESTAMP WITH TIME ZONE, 
	offer_token_used BOOLEAN, 
	offer_template_snapshot TEXT, 
	offer_pdf_path VARCHAR(500), 
	offer_accepted_ip VARCHAR(50), 
	offer_accepted_user_agent TEXT, 
	offer_email_status VARCHAR(20), 
	offer_email_retry_count INTEGER, 
	reminder_sent_at TIMESTAMP WITHOUT TIME ZONE, 
	employee_id VARCHAR(50), 
	id_card_url VARCHAR(500), 
	onboarded_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT check_applications_status CHECK (status IN ('applied', 'screened', 'aptitude_round', 'ai_interview', 'interview_scheduled', 'interview_completed', 'hired', 'pending_approval', 'offer_sent', 'accepted', 'rejected', 'onboarded', 'physical_interview')), 
	CONSTRAINT uq_application_job_email UNIQUE (job_id, candidate_email), 
	CONSTRAINT uq_application_job_phone_hash UNIQUE (job_id, candidate_phone_hash), 
	FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
	FOREIGN KEY(hr_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(offer_approved_by) REFERENCES users (id) ON DELETE SET NULL
)


CREATE INDEX ix_applications_job_id ON applications (job_id)
CREATE INDEX ix_applications_candidate_email ON applications (candidate_email)
CREATE INDEX ix_applications_candidate_phone_hash ON applications (candidate_phone_hash)
CREATE INDEX ix_applications_candidate_phone_normalized ON applications (candidate_phone_normalized)
CREATE INDEX ix_applications_hr_id ON applications (hr_id)
CREATE INDEX ix_applications_applied_at ON applications (applied_at)
CREATE UNIQUE INDEX ix_applications_offer_short_id ON applications (offer_short_id)
CREATE INDEX ix_applications_job_status ON applications (job_id, status)
CREATE INDEX ix_applications_status ON applications (status)
CREATE INDEX ix_applications_id ON applications (id)
CREATE INDEX ix_applications_resume_status ON applications (resume_status)
CREATE UNIQUE INDEX ix_applications_offer_token ON applications (offer_token)
CREATE UNIQUE INDEX ix_applications_employee_id ON applications (employee_id)
CREATE INDEX ix_applications_dashboard_filters ON applications (job_id, status, applied_at)
CREATE INDEX ix_applications_composite_score ON applications (composite_score)

CREATE TABLE job_versions (
	id SERIAL NOT NULL, 
	job_id INTEGER, 
	version_number INTEGER NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	primary_evaluated_skills TEXT, 
	experience_level VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_job_version UNIQUE (job_id, version_number), 
	FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE
)



CREATE TABLE application_stages (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	stage_name VARCHAR(100) NOT NULL, 
	stage_status VARCHAR(50), 
	score FLOAT, 
	evaluation_notes TEXT, 
	evaluator_id INTEGER, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(evaluator_id) REFERENCES users (id) ON DELETE SET NULL
)


CREATE INDEX ix_application_stages_id ON application_stages (id)
CREATE INDEX ix_application_stages_stage_status ON application_stages (stage_status)
CREATE INDEX ix_application_stages_application_id ON application_stages (application_id)
CREATE INDEX ix_application_stages_stage_name ON application_stages (stage_name)

CREATE TABLE resume_extractions (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	extracted_text TEXT, 
	summary TEXT, 
	extracted_skills TEXT, 
	years_of_experience FLOAT, 
	education TEXT, 
	previous_roles TEXT, 
	experience_level VARCHAR(50), 
	resume_score FLOAT, 
	skill_match_percentage FLOAT, 
	candidate_name VARCHAR(255), 
	email VARCHAR(255), 
	phone_number VARCHAR(50), 
	reasoning JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES applications (id)
)


CREATE INDEX ix_resume_extractions_id ON resume_extractions (id)
CREATE UNIQUE INDEX ix_resume_extractions_application_id ON resume_extractions (application_id)

CREATE TABLE interviews (
	id SERIAL NOT NULL, 
	test_id VARCHAR(50), 
	application_id INTEGER NOT NULL, 
	status VARCHAR(50), 
	locked_skill VARCHAR(50), 
	total_questions INTEGER, 
	questions_asked INTEGER, 
	current_difficulty VARCHAR(20), 
	overall_score FLOAT, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	ended_at TIMESTAMP WITHOUT TIME ZONE, 
	access_key_hash VARCHAR(255), 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	is_used BOOLEAN, 
	used_at TIMESTAMP WITHOUT TIME ZONE, 
	interview_stage VARCHAR(50), 
	aptitude_score FLOAT, 
	aptitude_completed_at TIMESTAMP WITHOUT TIME ZONE, 
	duration_minutes INTEGER, 
	aptitude_completed BOOLEAN, 
	first_level_completed BOOLEAN, 
	first_level_score FLOAT, 
	video_recording_path VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE
)


CREATE INDEX ix_interviews_id ON interviews (id)
CREATE INDEX ix_interviews_started_at ON interviews (started_at)
CREATE INDEX ix_interviews_status ON interviews (status)
CREATE UNIQUE INDEX ix_interviews_test_id ON interviews (test_id)
CREATE UNIQUE INDEX ix_interviews_application_id ON interviews (application_id)
CREATE INDEX ix_interviews_ended_at ON interviews (ended_at)

CREATE TABLE hiring_decisions (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	hr_id INTEGER, 
	decision VARCHAR(20) NOT NULL, 
	decision_comments TEXT, 
	joining_date TIMESTAMP WITHOUT TIME ZONE, 
	offer_letter_path VARCHAR(500), 
	decided_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT check_hiring_decision CHECK (decision IN ('hired', 'rejected')), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(hr_id) REFERENCES users (id) ON DELETE SET NULL
)


CREATE INDEX ix_hiring_decisions_id ON hiring_decisions (id)
CREATE UNIQUE INDEX ix_hiring_decisions_application_id ON hiring_decisions (application_id)
CREATE INDEX ix_hiring_decisions_hr_id ON hiring_decisions (hr_id)

CREATE TABLE interview_sessions (
	id SERIAL NOT NULL, 
	candidate_id INTEGER NOT NULL, 
	job_id INTEGER NOT NULL, 
	application_id INTEGER, 
	start_time TIMESTAMP WITH TIME ZONE, 
	end_time TIMESTAMP WITH TIME ZONE, 
	status VARCHAR(50), 
	final_score FLOAT, 
	difficulty_level VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(candidate_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE
)


CREATE INDEX ix_interview_sessions_job_id ON interview_sessions (job_id)
CREATE INDEX ix_interview_sessions_id ON interview_sessions (id)
CREATE INDEX ix_interview_sessions_candidate_id ON interview_sessions (candidate_id)
CREATE INDEX ix_interview_sessions_status ON interview_sessions (status)
CREATE INDEX ix_interview_sessions_application_id ON interview_sessions (application_id)

CREATE TABLE candidate_skills (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	skill_name VARCHAR(100) NOT NULL, 
	proficiency_score FLOAT, 
	years_experience FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE
)


CREATE INDEX ix_candidate_skills_application_id ON candidate_skills (application_id)
CREATE INDEX ix_candidate_skills_skill_name ON candidate_skills (skill_name)
CREATE INDEX ix_candidate_skills_id ON candidate_skills (id)

CREATE TABLE resume_extraction_versions (
	id SERIAL NOT NULL, 
	application_id INTEGER, 
	version_number INTEGER NOT NULL, 
	extracted_text TEXT, 
	extracted_skills TEXT, 
	resume_score FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_resume_version UNIQUE (application_id, version_number), 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE
)



CREATE TABLE interview_questions (
	id SERIAL NOT NULL, 
	interview_id INTEGER NOT NULL, 
	question_number INTEGER NOT NULL, 
	question_text TEXT NOT NULL, 
	question_type VARCHAR(50), 
	options TEXT, 
	correct_answer TEXT, 
	ai_generated_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(interview_id) REFERENCES interviews (id) ON DELETE CASCADE
)


CREATE INDEX ix_interview_questions_id ON interview_questions (id)
CREATE INDEX ix_interview_questions_interview_id ON interview_questions (interview_id)

CREATE TABLE interview_reports (
	id SERIAL NOT NULL, 
	interview_id INTEGER NOT NULL, 
	application_id INTEGER, 
	job_id INTEGER, 
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
	ai_used BOOLEAN, 
	fallback_used BOOLEAN, 
	reasoning JSON, 
	confidence_score FLOAT, 
	retry_count INTEGER, 
	failure_reason VARCHAR(1000), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(interview_id) REFERENCES interviews (id) ON DELETE CASCADE, 
	FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE
)


CREATE UNIQUE INDEX ix_interview_reports_interview_id ON interview_reports (interview_id)
CREATE INDEX ix_interview_reports_id ON interview_reports (id)
CREATE INDEX ix_interview_reports_job_id ON interview_reports (job_id)
CREATE INDEX ix_interview_reports_application_id ON interview_reports (application_id)

CREATE TABLE notifications (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	notification_type VARCHAR(50) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	is_read BOOLEAN, 
	related_application_id INTEGER, 
	related_interview_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	read_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(related_application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	FOREIGN KEY(related_interview_id) REFERENCES interviews (id) ON DELETE CASCADE
)


CREATE INDEX ix_notifications_created_at ON notifications (created_at)
CREATE INDEX ix_notifications_user_id ON notifications (user_id)
CREATE INDEX ix_notifications_id ON notifications (id)
CREATE INDEX ix_notifications_is_read ON notifications (is_read)

CREATE TABLE interview_issues (
	id SERIAL NOT NULL, 
	interview_id INTEGER NOT NULL, 
	candidate_name VARCHAR(255), 
	candidate_email VARCHAR(255), 
	issue_type VARCHAR(100), 
	description TEXT NOT NULL, 
	status VARCHAR(20), 
	hr_response TEXT, 
	is_reissue_granted BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT check_issue_status CHECK (status IN ('pending', 'resolved', 'dismissed')), 
	FOREIGN KEY(interview_id) REFERENCES interviews (id) ON DELETE CASCADE
)


CREATE INDEX ix_interview_issues_interview_id ON interview_issues (interview_id)
CREATE INDEX ix_interview_issues_candidate_email ON interview_issues (candidate_email)
CREATE INDEX ix_interview_issues_created_at ON interview_issues (created_at)
CREATE INDEX ix_interview_issues_id ON interview_issues (id)
CREATE INDEX ix_interview_issues_issue_type ON interview_issues (issue_type)
CREATE INDEX ix_interview_issues_status ON interview_issues (status)

CREATE TABLE interview_feedbacks (
	id SERIAL NOT NULL, 
	interview_id INTEGER NOT NULL, 
	ui_ux_rating INTEGER, 
	feedback_text TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(interview_id) REFERENCES interviews (id) ON DELETE CASCADE
)


CREATE INDEX ix_interview_feedbacks_id ON interview_feedbacks (id)
CREATE UNIQUE INDEX ix_interview_feedbacks_interview_id ON interview_feedbacks (interview_id)

CREATE TABLE interview_events (
	id SERIAL NOT NULL, 
	session_id INTEGER NOT NULL, 
	event_type VARCHAR(50) NOT NULL, 
	payload TEXT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES interview_sessions (id)
)


CREATE INDEX ix_interview_events_id ON interview_events (id)
CREATE INDEX ix_interview_events_created_at ON interview_events (created_at)
CREATE INDEX ix_interview_events_session_id ON interview_events (session_id)

CREATE TABLE interview_report_versions (
	id SERIAL NOT NULL, 
	interview_id INTEGER, 
	version_number INTEGER NOT NULL, 
	overall_score FLOAT, 
	summary TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_report_version UNIQUE (interview_id, version_number), 
	FOREIGN KEY(interview_id) REFERENCES interviews (id) ON DELETE CASCADE
)



CREATE TABLE interview_answers (
	id SERIAL NOT NULL, 
	question_id INTEGER NOT NULL, 
	interview_id INTEGER, 
	answer_text TEXT NOT NULL, 
	answer_score FLOAT, 
	answer_evaluation TEXT, 
	skill_relevance_score FLOAT, 
	technical_score FLOAT, 
	completeness_score FLOAT, 
	clarity_score FLOAT, 
	depth_score FLOAT, 
	practicality_score FLOAT, 
	ai_used BOOLEAN, 
	fallback_used BOOLEAN, 
	confidence_score FLOAT, 
	reasoning JSON, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	evaluated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_answer_per_question UNIQUE (question_id), 
	FOREIGN KEY(question_id) REFERENCES interview_questions (id) ON DELETE CASCADE, 
	FOREIGN KEY(interview_id) REFERENCES interviews (id) ON DELETE CASCADE
)


CREATE INDEX ix_interview_answers_id ON interview_answers (id)
CREATE INDEX ix_interview_answers_question_id ON interview_answers (question_id)
CREATE INDEX ix_interview_answers_interview_id ON interview_answers (interview_id)

CREATE TABLE ai_evaluations (
	id SERIAL NOT NULL, 
	answer_id INTEGER NOT NULL, 
	technical_score FLOAT, 
	communication_score FLOAT, 
	reasoning_score FLOAT, 
	feedback_text TEXT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(answer_id) REFERENCES interview_answers (id) ON DELETE CASCADE
)


CREATE INDEX ix_ai_evaluations_answer_id ON ai_evaluations (answer_id)
CREATE INDEX ix_ai_evaluations_id ON ai_evaluations (id)
