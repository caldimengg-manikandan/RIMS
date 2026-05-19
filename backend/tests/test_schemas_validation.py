"""
test_schemas_validation.py
==========================
Pure unit tests for Pydantic schemas in app.domain.schemas.
No database, no HTTP calls — entirely in-memory.
Covers: UserRegister, UserLogin, JobCreate, JobUpdate, ApplicationResponse,
        ResumeExtractionResponse, InterviewReportResponse, and more.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# 1.  UserRegister schema
# ══════════════════════════════════════════════════════════════════════════════

class TestUserRegisterSchema:
    """Validates the UserRegister Pydantic model field validators."""

    def _make(self, **kwargs):
        from app.domain.schemas import UserRegister
        defaults = {
            "email": "user@example.com",
            "password": "Secret123!",
            "full_name": "Test User",
        }
        defaults.update(kwargs)
        return UserRegister(**defaults)

    # --- Happy path ---

    def test_valid_registration(self):
        obj = self._make()
        assert obj.email == "user@example.com"
        assert obj.full_name == "Test User"

    def test_email_is_lowercased_and_trimmed(self):
        obj = self._make(email="  UPPER@Example.COM  ")
        assert obj.email == "upper@example.com"

    # --- Email edge cases ---

    def test_missing_at_symbol_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            self._make(email="invalidemail.com")
        assert "valid email" in str(exc_info.value).lower()

    def test_multiple_at_symbols_raises(self):
        with pytest.raises(ValidationError):
            self._make(email="a@@b.com")

    def test_double_dot_raises(self):
        with pytest.raises(ValidationError):
            self._make(email="user..name@example.com")

    def test_domain_starting_dot_raises(self):
        with pytest.raises(ValidationError):
            self._make(email="user@.example.com")

    def test_email_ending_in_dot_raises(self):
        with pytest.raises(ValidationError):
            self._make(email="user@example.")

    def test_empty_email_raises(self):
        with pytest.raises(ValidationError):
            self._make(email="")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  JobCreate schema
# ══════════════════════════════════════════════════════════════════════════════

class TestJobCreateSchema:
    """Validates the JobCreate Pydantic model field validators."""

    def _make(self, **kwargs):
        from app.domain.schemas import JobCreate
        defaults = {
            "title": "Software Engineer",
            "description": "Build and maintain web applications and APIs.",
            "experience_level": "mid",
        }
        defaults.update(kwargs)
        return JobCreate(**defaults)

    # --- Happy path ---

    def test_valid_job(self):
        obj = self._make()
        assert obj.title == "Software Engineer"

    def test_title_stripped_of_whitespace(self):
        obj = self._make(title="  DevOps Engineer  ")
        assert obj.title == "DevOps Engineer"

    def test_optional_fields_default_correctly(self):
        obj = self._make()
        assert obj.duration_minutes == 60
        assert obj.aptitude_enabled is False
        assert obj.mode_of_work == "Remote"

    # --- Title validation ---

    def test_numeric_only_title_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            self._make(title="123456")
        assert "letters" in str(exc_info.value).lower()

    def test_too_short_title_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            self._make(title="AB")
        assert "3 characters" in str(exc_info.value)

    def test_special_char_title_raises(self):
        with pytest.raises(ValidationError):
            self._make(title="Engineer@Corp!")

    def test_allowed_symbols_in_title(self):
        """Titles with +, #, ., - should be accepted."""
        obj = self._make(title="C++ Developer")
        assert obj.title == "C++ Developer"

    def test_dotnet_title_accepted(self):
        obj = self._make(title=".NET Engineer")
        assert obj.title == ".NET Engineer"

    # --- Description validation ---

    def test_short_description_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            self._make(description="Too short")
        assert "10 characters" in str(exc_info.value)

    def test_numeric_only_description_raises(self):
        with pytest.raises(ValidationError):
            self._make(description="1234567890")

    # --- Duration validation ---

    def test_duration_too_low_raises(self):
        with pytest.raises(ValidationError):
            self._make(duration_minutes=0)

    def test_duration_too_high_raises(self):
        with pytest.raises(ValidationError):
            self._make(duration_minutes=301)

    def test_boundary_duration_accepted(self):
        obj = self._make(duration_minutes=1)
        assert obj.duration_minutes == 1
        obj2 = self._make(duration_minutes=300)
        assert obj2.duration_minutes == 300

    # --- Requirements validation ---

    def test_valid_requirements_accepted(self):
        obj = self._make(requirements="Minimum 3 years of Python backend experience.")
        assert obj.requirements is not None

    def test_too_short_requirements_raises(self):
        with pytest.raises(ValidationError):
            self._make(requirements="Short")

    def test_none_requirements_accepted(self):
        obj = self._make(requirements=None)
        assert obj.requirements is None


# ══════════════════════════════════════════════════════════════════════════════
# 3.  JobUpdate schema
# ══════════════════════════════════════════════════════════════════════════════

class TestJobUpdateSchema:
    """Validates the JobUpdate Pydantic model (all optional fields)."""

    def _make(self, **kwargs):
        from app.domain.schemas import JobUpdate
        return JobUpdate(**kwargs)

    def test_empty_update_is_valid(self):
        """All fields optional — empty update should pass."""
        obj = self._make()
        assert obj.title is None

    def test_update_title_validates(self):
        with pytest.raises(ValidationError):
            self._make(title="12")  # Too short

    def test_update_duration_validates(self):
        with pytest.raises(ValidationError):
            self._make(duration_minutes=500)

    def test_valid_partial_update(self):
        obj = self._make(title="Updated Engineer Title", duration_minutes=90)
        assert obj.title == "Updated Engineer Title"
        assert obj.duration_minutes == 90


# ══════════════════════════════════════════════════════════════════════════════
# 4.  ApplicationResponse score clamping
# ══════════════════════════════════════════════════════════════════════════════

class TestApplicationResponseScoreClamping:
    """Validates that scores are clamped to [0, 100] range."""

    def _base_data(self):
        return {
            "id": 1,
            "job_id": 1,
            "candidate_name": "Jane Doe",
            "candidate_email": "jane@example.com",
            "resume_file_name": "resume.pdf",
            "resume_file_path": "/resumes/resume.pdf",
            "status": "applied",
            "hr_id": 1,
            "resume_status": "parsed",
            "applied_at": _now_iso(),
            "updated_at": _now_iso(),
        }

    def _make(self, **kwargs):
        from app.domain.schemas import ApplicationResponse
        data = self._base_data()
        data.update(kwargs)
        return ApplicationResponse(**data)

    def test_normal_scores_pass_through(self):
        obj = self._make(resume_score=85.5, aptitude_score=72.0, interview_score=90.0)
        assert obj.resume_score == 85.5
        assert obj.aptitude_score == 72.0
        assert obj.interview_score == 90.0

    def test_score_above_100_clamped(self):
        obj = self._make(resume_score=150.0)
        assert obj.resume_score == 100.0

    def test_score_below_0_clamped(self):
        obj = self._make(resume_score=-10.0)
        assert obj.resume_score == 0.0

    def test_none_score_becomes_zero(self):
        obj = self._make(resume_score=None)
        assert obj.resume_score == 0.0

    def test_string_score_coerced_to_float(self):
        obj = self._make(resume_score="78.5")
        assert obj.resume_score == 78.5

    def test_invalid_string_score_becomes_zero(self):
        obj = self._make(resume_score="not-a-number")
        assert obj.resume_score == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 5.  ResumeExtractionResponse
# ══════════════════════════════════════════════════════════════════════════════

class TestResumeExtractionResponseSchema:
    """Tests for ResumeExtractionResponse validation including JSON reasoning."""

    def _make(self, **kwargs):
        from app.domain.schemas import ResumeExtractionResponse
        defaults = {
            "id": 1,
            "application_id": 1,
            "extracted_text": "Sample extracted text content",
            "summary": "Experienced Python developer",
            "extracted_skills": '["Python", "FastAPI"]',
            "years_of_experience": 3.0,
            "education": "B.Tech Computer Science",
            "previous_roles": "Backend Developer",
            "experience_level": "mid",
            "resume_score": 80.0,
            "skill_match_percentage": 75.0,
            "created_at": _now_iso(),
        }
        defaults.update(kwargs)
        return ResumeExtractionResponse(**defaults)

    def test_valid_extraction(self):
        obj = self._make()
        assert obj.resume_score == 80.0

    def test_reasoning_json_string_parsed(self):
        obj = self._make(reasoning='{"score": 80, "comment": "Good match"}')
        assert isinstance(obj.reasoning, dict)
        assert obj.reasoning["score"] == 80

    def test_reasoning_invalid_json_returns_error_dict(self):
        obj = self._make(reasoning="not-valid-json")
        assert isinstance(obj.reasoning, dict)
        assert "error" in obj.reasoning

    def test_reasoning_dict_passthrough(self):
        obj = self._make(reasoning={"score": 90})
        assert obj.reasoning["score"] == 90

    def test_score_clamped_above_100(self):
        obj = self._make(resume_score=200.0)
        assert obj.resume_score == 100.0


# ══════════════════════════════════════════════════════════════════════════════
# 6.  InterviewReportResponse
# ══════════════════════════════════════════════════════════════════════════════

class TestInterviewReportResponseSchema:
    """Tests for InterviewReportResponse score clamping and reasoning parsing."""

    def _make(self, **kwargs):
        from app.domain.schemas import InterviewReportResponse
        defaults = {
            "id": 1,
            "interview_id": 1,
            "candidate_name": "John Smith",
            "candidate_email": "john@example.com",
            "applied_role": "Software Engineer",
            "overall_score": 85.0,
            "technical_skills_score": 90.0,
            "communication_score": 80.0,
            "problem_solving_score": 75.0,
            "summary": "Strong candidate",
            "strengths": "Problem solving",
            "weaknesses": "Communication",
            "recommendation": "recommended",
            "detailed_feedback": "Detailed feedback text here.",
            "created_at": _now_iso(),
        }
        defaults.update(kwargs)
        return InterviewReportResponse(**defaults)

    def test_valid_report(self):
        obj = self._make()
        assert obj.overall_score == 85.0

    def test_negative_score_clamped_to_zero(self):
        obj = self._make(overall_score=-5.0)
        assert obj.overall_score == 0.0

    def test_score_above_100_clamped(self):
        obj = self._make(technical_skills_score=120.0)
        assert obj.technical_skills_score == 100.0

    def test_none_score_becomes_zero(self):
        obj = self._make(aptitude_score=None)
        assert obj.aptitude_score == 0.0

    def test_reasoning_parsed_from_json_string(self):
        obj = self._make(reasoning='{"rationale": "clear answers"}')
        assert obj.reasoning["rationale"] == "clear answers"

    def test_reasoning_invalid_json_has_error_key(self):
        obj = self._make(reasoning="{{bad json}}")
        assert "error" in obj.reasoning


# ══════════════════════════════════════════════════════════════════════════════
# 7.  InterviewIssueCreate / InterviewIssueResolve
# ══════════════════════════════════════════════════════════════════════════════

class TestTicketSchemas:

    def test_valid_issue_create(self):
        from app.domain.schemas import InterviewIssueCreate
        obj = InterviewIssueCreate(
            interview_id=1,
            issue_type="technical",
            description="My webcam stopped working midway",
        )
        assert obj.interview_id == 1

    def test_valid_issue_resolve(self):
        from app.domain.schemas import InterviewIssueResolve
        obj = InterviewIssueResolve(hr_response="We will reschedule.", action="resolve", send_email=True)
        assert obj.action == "resolve"

    def test_resolve_without_hr_response_defaults_empty(self):
        from app.domain.schemas import InterviewIssueResolve
        obj = InterviewIssueResolve(action="dismiss")
        assert obj.hr_response == ""

    def test_send_email_defaults_true(self):
        from app.domain.schemas import InterviewIssueResolve
        obj = InterviewIssueResolve(action="resolve")
        assert obj.send_email is True


# ══════════════════════════════════════════════════════════════════════════════
# 8.  TokenResponse / UserResponse
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthResponseSchemas:

    def test_token_response_defaults_bearer(self):
        from app.domain.schemas import TokenResponse
        obj = TokenResponse(access_token="abc.def.ghi")
        assert obj.token_type == "bearer"

    def test_user_response_from_orm_like_dict(self):
        from app.domain.schemas import UserResponse
        obj = UserResponse(
            id=1,
            email="hr@test.com",
            full_name="HR Manager",
            role="hr",
            is_active=True,
            is_verified=True,
            approval_status="approved",
            created_at=_now_iso(),
        )
        assert obj.role == "hr"
        assert obj.profile_image_url is None

    def test_user_response_created_at_iso_string_parsed(self):
        from app.domain.schemas import UserResponse
        obj = UserResponse(
            id=2,
            email="test@test.com",
            full_name="Test",
            role="candidate",
            is_active=True,
            is_verified=False,
            approval_status="pending",
            created_at="2024-01-15T10:30:00Z",
        )
        assert obj.created_at is not None


# ══════════════════════════════════════════════════════════════════════════════
# 9.  ForgotPassword / ResetPassword schemas
# ══════════════════════════════════════════════════════════════════════════════

class TestPasswordSchemas:

    def test_forgot_password_valid_email(self):
        from app.domain.schemas import ForgotPasswordRequest
        obj = ForgotPasswordRequest(email="user@example.com")
        assert obj.email == "user@example.com"

    def test_forgot_password_invalid_email_raises(self):
        from app.domain.schemas import ForgotPasswordRequest
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="notanemail")

    def test_reset_password_valid(self):
        from app.domain.schemas import ResetPasswordRequest
        obj = ResetPasswordRequest(email="user@example.com", otp="123456", new_password="NewPass1!")
        assert obj.otp == "123456"

    def test_reset_password_invalid_email_raises(self):
        from app.domain.schemas import ResetPasswordRequest
        with pytest.raises(ValidationError):
            ResetPasswordRequest(email="bad@@email", otp="111111", new_password="Test1!")


# ══════════════════════════════════════════════════════════════════════════════
# 10.  InterviewFeedbackCreate
# ══════════════════════════════════════════════════════════════════════════════

class TestInterviewFeedbackSchema:

    def test_valid_feedback(self):
        from app.domain.schemas import InterviewFeedbackCreate
        obj = InterviewFeedbackCreate(interview_id=1, ui_ux_rating=4, feedback_text="Very smooth experience")
        assert obj.ui_ux_rating == 4

    def test_feedback_text_is_optional(self):
        from app.domain.schemas import InterviewFeedbackCreate
        obj = InterviewFeedbackCreate(interview_id=1, ui_ux_rating=5)
        assert obj.feedback_text is None


# ══════════════════════════════════════════════════════════════════════════════
# 11.  ApplicationListResponse pagination
# ══════════════════════════════════════════════════════════════════════════════

class TestApplicationListResponseSchema:

    def test_empty_items(self):
        from app.domain.schemas import ApplicationListResponse
        obj = ApplicationListResponse(items=[], total=0, page=1, size=20, pages=0)
        assert obj.total == 0
        assert obj.items == []
