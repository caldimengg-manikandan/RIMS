import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_register_candidate(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "new_test_candidate@domain.com", "password": "SecurePassword123!", "full_name": "Test User"}
    )
    # The register endpoint returns the User object directly
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["email"] == "new_test_candidate@domain.com"

def test_login_invalid_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@domain.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    # The application error format is {"success": False, "data": None, "error": "..."}
    assert "Invalid credentials" in response.json()["error"]

def test_idor_job_access(client, candidate_auth_headers):
    # Use real candidate auth headers from fixture
    response = client.put(
        "/api/jobs/1",
        json={"title": "Hacked Title"},
        headers=candidate_auth_headers
    )
    assert response.status_code == 403 # Candidate cannot edit HR jobs
