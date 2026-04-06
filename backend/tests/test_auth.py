import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_candidate():
    response = client.post(
        "/api/auth/register",
        json={"email": "test_candidate@domain.com", "password": "SecurePassword123!", "full_name": "Test User"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Registration successful"

def test_login_invalid_credentials():
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@domain.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_idor_job_access(mocker):
    # Mock JWT authentication
    headers = {"Authorization": "Bearer mocked_candidate_token"}
    response = client.put(
        "/api/jobs/1",
        json={"title": "Hacked Title"},
        headers=headers
    )
    assert response.status_code == 403 # Candidate cannot edit HR jobs
