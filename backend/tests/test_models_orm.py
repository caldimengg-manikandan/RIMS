"""
test_models_orm.py
==================
ORM-level unit tests using an in-memory SQLite database (via conftest fixtures).

Tests:
 - Creating and querying User, Job, Application, Interview models
 - Relationship traversal (job.applications, application.job)
 - Constraint checks
 - Encryption round-trip on EncryptedText columns
 - Defaults (timestamps, status, etc.)
"""

import pytest
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
# 1.  User model
# ══════════════════════════════════════════════════════════════════════════════

class TestUserModel:

    def test_create_hr_user(self, db_session):
        from app.domain.models import User
        u = User(
            email="hr2@test.com",
            password_hash="hashed_pw",
            full_name="HR User",
            role="hr",
            is_active=True,
            is_verified=True,
            approval_status="approved",
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        assert u.id is not None
        assert u.role == "hr"

    def test_create_candidate_user(self, db_session):
        from app.domain.models import User
        u = User(
            email="cand2@test.com",
            password_hash="hashed_pw",
            full_name="Candidate User",
            role="candidate",
            is_active=True,
            is_verified=False,
            approval_status="pending",
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        assert u.is_verified is False
        assert u.approval_status == "pending"

    def test_user_defaults(self, db_session):
        """Verify default values for is_active and is_verified."""
        from app.domain.models import User
        u = User(
            email="defaults@test.com",
            password_hash="hashed",
            full_name="Default User",
            role="candidate",
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        # Defaults from model definition
        assert u.is_active is False
        assert u.is_verified is False

    def test_user_email_unique_constraint(self, db_session, sample_hr_user):
        """Inserting duplicate email should raise."""
        from app.domain.models import User
        from sqlalchemy.exc import IntegrityError
        u2 = User(
            email=sample_hr_user.email,  # Duplicate
            password_hash="hashed",
            full_name="Duplicate",
            role="candidate",
        )
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_created_at_auto_populated(self, db_session):
        from app.domain.models import User
        u = User(
            email="timestamps@test.com",
            password_hash="hashed",
            full_name="Timestamp User",
            role="candidate",
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        # created_at should have been set automatically
        assert u.created_at is not None

    def test_fixture_hr_user_has_correct_role(self, sample_hr_user):
        assert sample_hr_user.role == "hr"
        assert sample_hr_user.is_active is True

    def test_fixture_candidate_user_has_correct_role(self, sample_candidate_user):
        assert sample_candidate_user.role == "candidate"


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Job model
# ══════════════════════════════════════════════════════════════════════════════

class TestJobModel:

    def test_create_job(self, db_session, sample_hr_user):
        from app.domain.models import Job
        job = Job(
            title="Backend Developer",
            description="Develop APIs using FastAPI and PostgreSQL.",
            experience_level="senior",
            hr_id=sample_hr_user.id,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        assert job.id is not None
        assert job.status == "open"  # Default

    def test_job_default_status_is_open(self, sample_job):
        assert sample_job.status == "open"

    def test_job_default_duration_is_60(self, sample_job):
        assert sample_job.duration_minutes == 60

    def test_job_default_aptitude_disabled(self, sample_job):
        assert sample_job.aptitude_enabled is False

    def test_job_hr_relationship(self, db_session, sample_job, sample_hr_user):
        """Job.hr should point back to the HR user."""
        db_session.refresh(sample_job)
        # Load the hr via relationship
        hr = db_session.query(sample_job.__class__).get(sample_job.id).hr_id
        assert hr == sample_hr_user.id

    def test_job_with_aptitude_enabled(self, db_session, sample_hr_user):
        from app.domain.models import Job
        job = Job(
            title="Data Scientist",
            description="Machine learning model development and deployment.",
            experience_level="senior",
            hr_id=sample_hr_user.id,
            aptitude_enabled=True,
            duration_minutes=90,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        assert job.aptitude_enabled is True
        assert job.duration_minutes == 90

    def test_query_job_by_id(self, db_session, sample_job):
        from app.domain.models import Job
        fetched = db_session.query(Job).get(sample_job.id)
        assert fetched is not None
        assert fetched.title == sample_job.title


# ══════════════════════════════════════════════════════════════════════════════
# 3.  Application model
# ══════════════════════════════════════════════════════════════════════════════

class TestApplicationModel:

    def test_create_application(self, db_session, sample_job):
        from app.domain.models import Application
        app = Application(
            job_id=sample_job.id,
            hr_id=sample_job.hr_id,
            candidate_name="Alice Test",
            candidate_email="alice@test.com",
            resume_file_name="alice.pdf",
            resume_file_path="/resumes/alice.pdf",
            status="applied",
            resume_status="pending",
        )
        db_session.add(app)
        db_session.commit()
        db_session.refresh(app)
        assert app.id is not None
        assert app.status == "applied"

    def test_application_default_resume_status(self, db_session, sample_job):
        from app.domain.models import Application
        app = Application(
            job_id=sample_job.id,
            hr_id=sample_job.hr_id,
            candidate_name="Bob Test",
            candidate_email="bob@test.com",
            resume_file_name="bob.pdf",
            resume_file_path="/resumes/bob.pdf",
        )
        db_session.add(app)
        db_session.commit()
        db_session.refresh(app)
        assert app.resume_status == "pending"  # Default

    def test_application_default_scores_zero(self, db_session, sample_job):
        from app.domain.models import Application
        app = Application(
            job_id=sample_job.id,
            hr_id=sample_job.hr_id,
            candidate_name="Carol Test",
            candidate_email="carol@test.com",
        )
        db_session.add(app)
        db_session.commit()
        db_session.refresh(app)
        assert app.resume_score == 0
        assert app.composite_score == 0

    def test_sample_application_fixture(self, sample_application):
        assert sample_application.status == "applied"
        assert sample_application.candidate_email == "jane@example.com"
        assert sample_application.resume_score == 75.0

    def test_application_unique_job_email_constraint(self, db_session, sample_job, sample_application):
        """Cannot apply to the same job with the same email twice."""
        from app.domain.models import Application
        from sqlalchemy.exc import IntegrityError
        dup = Application(
            job_id=sample_application.job_id,
            hr_id=sample_job.hr_id,
            candidate_name="Jane Duplicate",
            candidate_email=sample_application.candidate_email,  # Same email + job
        )
        db_session.add(dup)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_application_notes_encrypted(self, db_session, sample_application):
        """HR notes should be stored encrypted and retrieved as plaintext."""
        from app.domain.models import Application
        secret_note = "Do not shortlist — cultural mismatch"
        sample_application.hr_notes = secret_note
        db_session.commit()
        db_session.refresh(sample_application)
        # After round-trip, we should get the plain text back
        assert sample_application.hr_notes == secret_note

    def test_application_status_update(self, db_session, sample_application):
        sample_application.status = "screened"
        db_session.commit()
        db_session.refresh(sample_application)
        assert sample_application.status == "screened"


# ══════════════════════════════════════════════════════════════════════════════
# 4.  Interview model
# ══════════════════════════════════════════════════════════════════════════════

class TestInterviewModel:

    def test_create_interview(self, db_session, sample_application):
        from app.domain.models import Interview
        interview = Interview(
            application_id=sample_application.id,
            status="not_started",
            total_questions=10,
            questions_asked=0,
        )
        db_session.add(interview)
        db_session.commit()
        db_session.refresh(interview)
        assert interview.id is not None
        assert interview.status == "not_started"

    def test_interview_default_status(self, sample_interview):
        assert sample_interview.status == "not_started"
        assert sample_interview.questions_asked == 0

    def test_interview_status_update(self, db_session, sample_interview):
        sample_interview.status = "in_progress"
        db_session.commit()
        db_session.refresh(sample_interview)
        assert sample_interview.status == "in_progress"

    def test_interview_default_duration(self, sample_interview):
        assert sample_interview.duration_minutes == 60

    def test_interview_application_relationship(self, db_session, sample_interview, sample_application):
        """Interview.application should resolve correctly."""
        db_session.refresh(sample_interview)
        assert sample_interview.application_id == sample_application.id


# ══════════════════════════════════════════════════════════════════════════════
# 5.  InterviewQuestion and InterviewAnswer models
# ══════════════════════════════════════════════════════════════════════════════

class TestInterviewQuestionsAnswers:

    def test_create_question(self, db_session, sample_interview):
        from app.domain.models import InterviewQuestion
        q = InterviewQuestion(
            interview_id=sample_interview.id,
            question_number=1,
            question_text="Explain REST vs GraphQL",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)
        assert q.id is not None
        assert q.question_type == "technical"

    def test_create_answer_for_question(self, db_session, sample_interview):
        from app.domain.models import InterviewQuestion, InterviewAnswer
        q = InterviewQuestion(
            interview_id=sample_interview.id,
            question_number=2,
            question_text="What is dependency injection?",
            question_type="technical",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)

        a = InterviewAnswer(
            question_id=q.id,
            interview_id=sample_interview.id,
            answer_text="Dependency injection allows...",
            answer_score=8.5,
        )
        db_session.add(a)
        db_session.commit()
        db_session.refresh(a)
        assert a.id is not None
        assert a.answer_score == 8.5

    def test_answer_text_encrypted_round_trip(self, db_session, sample_interview):
        """Answer text stored as EncryptedText should survive round-trip."""
        from app.domain.models import InterviewQuestion, InterviewAnswer
        q = InterviewQuestion(
            interview_id=sample_interview.id,
            question_number=3,
            question_text="Describe SOLID principles",
            question_type="behavioral",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)

        secret_answer = "SOLID stands for Single Responsibility, Open-Closed..."
        a = InterviewAnswer(
            question_id=q.id,
            interview_id=sample_interview.id,
            answer_text=secret_answer,
        )
        db_session.add(a)
        db_session.commit()
        db_session.refresh(a)
        assert a.answer_text == secret_answer


# ══════════════════════════════════════════════════════════════════════════════
# 6.  AuditLog model
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditLogModel:

    def test_create_audit_log(self, db_session, sample_hr_user):
        from app.domain.models import AuditLog
        log = AuditLog(
            user_id=sample_hr_user.id,
            action="STATE_TRANSITION",
            resource_type="Application",
            resource_id=1,
            details='{"from_state": "applied", "to_state": "screened"}',
            is_critical=False,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        assert log.id is not None
        assert log.action == "STATE_TRANSITION"

    def test_audit_log_no_user_id(self, db_session):
        """Audit logs can be created without a user (system actions)."""
        from app.domain.models import AuditLog
        log = AuditLog(
            user_id=None,
            action="SYSTEM_HEALTH_CHECK",
            resource_type="System",
            resource_id=None,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        assert log.user_id is None


# ══════════════════════════════════════════════════════════════════════════════
# 7.  Notification model
# ══════════════════════════════════════════════════════════════════════════════

class TestNotificationModel:

    def test_create_notification(self, db_session, sample_hr_user, sample_application):
        from app.domain.models import Notification
        notif = Notification(
            user_id=sample_hr_user.id,
            notification_type="application_update",
            title="New Application",
            message="A new candidate has applied to your job.",
            is_read=False,
            related_application_id=sample_application.id,
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)
        assert notif.id is not None
        assert notif.is_read is False

    def test_notification_message_encrypted(self, db_session, sample_hr_user, sample_application):
        """Notification message uses EncryptedText — should round-trip correctly."""
        from app.domain.models import Notification
        message = "Candidate Jane Doe submitted a new resume."
        notif = Notification(
            user_id=sample_hr_user.id,
            notification_type="resume_update",
            title="Resume Submitted",
            message=message,
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)
        assert notif.message == message

    def test_mark_notification_read(self, db_session, sample_hr_user):
        from app.domain.models import Notification
        notif = Notification(
            user_id=sample_hr_user.id,
            notification_type="general",
            title="Test",
            message="Test message.",
            is_read=False,
        )
        db_session.add(notif)
        db_session.commit()

        notif.is_read = True
        db_session.commit()
        db_session.refresh(notif)
        assert notif.is_read is True


# ══════════════════════════════════════════════════════════════════════════════
# 8.  HiringDecision model
# ══════════════════════════════════════════════════════════════════════════════

class TestHiringDecisionModel:

    def test_create_hiring_decision(self, db_session, sample_application, sample_hr_user):
        from app.domain.models import HiringDecision
        decision = HiringDecision(
            application_id=sample_application.id,
            hr_id=sample_hr_user.id,
            decision="hired",
            decision_comments="Excellent candidate with great problem solving skills.",
        )
        db_session.add(decision)
        db_session.commit()
        db_session.refresh(decision)
        assert decision.id is not None
        assert decision.decision == "hired"

    def test_create_rejection_decision(self, db_session, sample_application, sample_hr_user):
        from app.domain.models import HiringDecision
        decision = HiringDecision(
            application_id=sample_application.id,
            hr_id=sample_hr_user.id,
            decision="rejected",
            decision_comments="Lacked the required technical depth.",
        )
        db_session.add(decision)
        db_session.commit()
        db_session.refresh(decision)
        assert decision.decision == "rejected"


# ══════════════════════════════════════════════════════════════════════════════
# 9.  GlobalSettings model
# ══════════════════════════════════════════════════════════════════════════════

class TestGlobalSettingsModel:

    def test_create_setting(self, db_session):
        from app.domain.models import GlobalSettings
        setting = GlobalSettings(
            key="company_name",
            value="ACME Corp",
        )
        db_session.add(setting)
        db_session.commit()
        db_session.refresh(setting)
        assert setting.id is not None
        assert setting.value == "ACME Corp"

    def test_setting_unique_key_constraint(self, db_session):
        from app.domain.models import GlobalSettings
        from sqlalchemy.exc import IntegrityError
        s1 = GlobalSettings(key="unique_key_test", value="value1")
        s2 = GlobalSettings(key="unique_key_test", value="value2")
        db_session.add(s1)
        db_session.commit()
        db_session.add(s2)
        with pytest.raises(IntegrityError):
            db_session.commit()
