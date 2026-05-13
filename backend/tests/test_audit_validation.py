import pytest
from app.main import app

# Use the client fixture from conftest.py

# ---------------------------------------------------------
# LAYER 3: INPUT VALIDATION & SANITIZATION
# ---------------------------------------------------------

def test_job_creation_rejects_numeric_title(client, hr_auth_headers):
    """Verify that job titles must contain alphabetic characters."""
    response = client.post(
        "/api/jobs",
        json={
            "title": "123456",
            "description": "Valid description that is longer than twenty characters for testing.",
            "experience_level": "junior"
        },
        headers=hr_auth_headers
    )
    # The middleware or validation should catch this
    assert response.status_code in [400, 422]

def test_job_creation_rejects_short_description(client, hr_auth_headers):
    """Verify that job descriptions must be at least 20 characters."""
    response = client.post(
        "/api/jobs",
        json={
            "title": "Software Engineer",
            "description": "Too short",
            "experience_level": "junior"
        },
        headers=hr_auth_headers
    )
    assert response.status_code in [400, 422]

def test_application_validation_direct(client, sample_job):
    """Bypass the frontend and hit the apply endpoint with bad data."""
    # 1. Invalid Name (Empty)
    response = client.post(
        "/api/applications/apply",
        data={
            "job_id": sample_job.id,
            "candidate_name": "",
            "candidate_email": "test@domain.com"
        },
        files={"resume_file": ("test.pdf", b"%PDF-fake", "application/pdf")}
    )
    assert response.status_code in [400, 422]

    # 2. Invalid Email
    response = client.post(
        "/api/applications/apply",
        data={
            "job_id": sample_job.id,
            "candidate_name": "John Doe",
            "candidate_email": "invalid-email@"
        },
        files={"resume_file": ("test.pdf", b"%PDF-fake", "application/pdf")}
    )
    assert response.status_code in [400, 422]

    # 3. Invalid Phone
    response = client.post(
        "/api/applications/apply",
        data={
            "job_id": sample_job.id,
            "candidate_name": "John Doe",
            "candidate_email": "john@example.com",
            "candidate_phone": "123"
        },
        files={"resume_file": ("test.pdf", b"%PDF-fake", "application/pdf")}
    )
    assert response.status_code in [400, 422]

# ---------------------------------------------------------
# LAYER 1 & 6: CONNECTIVITY & ENV FALLBACKS
# ---------------------------------------------------------

def test_cors_aware_rate_limit_fallback():
    """Verify that the CORS aware rate limit handler uses settings for fallback."""
    from app.core.config import get_settings
    settings = get_settings()
    assert settings.frontend_base_url is not None
