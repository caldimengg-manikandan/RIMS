import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from jose import jwt
import datetime
import html

from app.domain.models import InterviewIssue, Interview, Application, User
from app.core.config import get_settings

def make_interview_token(interview_id: int) -> str:
    settings = get_settings()
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(interview_id),
        "role": "interview",
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_unauthenticated_api_endpoints(client: TestClient):
    """Unauthenticated users should be blocked from retrieving ticket info or counts."""
    # List tickets without token
    resp = client.get("/api/tickets")
    assert resp.status_code == 401
    
    # Get ticket counts without token
    resp_cnt = client.get("/api/tickets/count")
    assert resp_cnt.status_code == 401


def test_candidate_issue_reporting_and_sanitization(client: TestClient, sample_interview: Interview, db_session: Session):
    """Verify ticket reporting, token constraints, input length limitations, and HTML escaping."""
    interview_token = make_interview_token(sample_interview.id)
    headers = {"Authorization": f"Bearer {interview_token}"}
    
    # 1. Block mismatched interview_id report
    resp = client.post("/api/tickets", json={
        "interview_id": sample_interview.id + 1,
        "issue_type": "technical",
        "description": "Tab switch error"
    }, headers=headers)
    assert resp.status_code == 403
    assert "Interview token does not match" in resp.json()["error"]
    
    # 2. Block description exceeding 5000 characters
    resp_long = client.post("/api/tickets", json={
        "interview_id": sample_interview.id,
        "issue_type": "technical",
        "description": "A" * 6000
    }, headers=headers)
    assert resp_long.status_code == 400
    assert "Description exceeds maximum allowed length" in resp_long.json()["error"]
    
    # 3. Test XSS / HTML Injection sanitization on success
    xss_payload = {
        "interview_id": sample_interview.id,
        "issue_type": "technical",
        "description": "<b>HTML Content</b><script>alert('XSS')</script>"
    }
    resp_ok = client.post("/api/tickets", json=xss_payload, headers=headers)
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert "&lt;b&gt;" in data["description"]
    assert "&lt;script&gt;" in data["description"]
    assert "<script>" not in data["description"]


def test_grievance_email_enumeration_protection(client: TestClient):
    """Verify that report_grievance returns unified 401 to prevent email enumeration."""
    # Try non-existent email
    payload = {
        "email": "ghost_candidate@example.com",
        "access_key": "some_key_123",
        "issue_type": "technical",
        "description": "Issue with video"
    }
    resp = client.post("/api/tickets/grievance", json=payload)
    assert resp.status_code == 401
    assert "Invalid email or access key" in resp.json()["error"]


def test_collaborative_hr_ticket_resolution_flow(
    client: TestClient, 
    sample_interview: Interview, 
    hr_auth_headers: dict, 
    db_session: Session
):
    """Verify collaborative HR management (reply, dismiss, resolve, and reissue_key) is 100% functional."""
    # Setup a pending ticket
    app_record = sample_interview.application
    ticket = InterviewIssue(
        interview_id=sample_interview.id,
        candidate_name=app_record.candidate_name,
        candidate_email=app_record.candidate_email,
        issue_type="technical",
        description="Lost tab focus during proctoring",
        status="pending"
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    
    # 1. Verify collaborative hr count & list
    count_resp = client.get("/api/tickets/count", headers=hr_auth_headers)
    assert count_resp.status_code == 200
    assert count_resp.json()["count"] > 0
    
    list_resp = client.get("/api/tickets?status=pending", headers=hr_auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) > 0

    # 2. Test action: reply (status remains pending)
    reply_resp = client.put(f"/api/tickets/{ticket.id}/resolve", json={
        "action": "reply",
        "hr_response": "We are investigating.",
        "send_email": False
    }, headers=hr_auth_headers)
    assert reply_resp.status_code == 200
    assert reply_resp.json()["status"] == "pending"
    assert "We are investigating" in reply_resp.json()["hr_response"]

    # 3. Test action: dismiss (status becomes dismissed)
    dismiss_resp = client.put(f"/api/tickets/{ticket.id}/resolve", json={
        "action": "dismiss",
        "hr_response": "Dismissed interruption.",
        "send_email": False
    }, headers=hr_auth_headers)
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["status"] == "dismissed"

    # Reset ticket status to pending for next tests
    ticket.status = "pending"
    db_session.commit()

    # 4. Test action: resolve (status becomes resolved)
    resolve_resp = client.put(f"/api/tickets/{ticket.id}/resolve", json={
        "action": "resolve",
        "hr_response": "Resolved issue.",
        "send_email": False
    }, headers=hr_auth_headers)
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "resolved"

    # Reset ticket status to pending for next tests
    ticket.status = "pending"
    db_session.commit()

    # 5. Test action: reissue_key (resets interview session & generates new key)
    reissue_resp = client.put(f"/api/tickets/{ticket.id}/resolve", json={
        "action": "reissue_key",
        "hr_response": "Access key regenerated.",
        "send_email": False
    }, headers=hr_auth_headers)
    assert reissue_resp.status_code == 200
    assert reissue_resp.json()["status"] == "resolved"
    assert reissue_resp.json()["is_reissue_granted"] is True
    
    # Reload interview from database to assert it is reset
    db_session.refresh(sample_interview)
    assert sample_interview.status == "not_started"
    assert sample_interview.is_used is False


def test_candidate_support_ticket_creation(client: TestClient, sample_interview: Interview, db_session: Session):
    """Verify that the new /api/support/ticket endpoint accepts valid candidate payloads without crashing."""
    # This simulates a candidate trying to report a ticket using their actual offer/interview access key
    # Wait, we need to pass the raw access key, not the hash. Since the test fixture uses a pre-hashed key, 
    # we can bypass the auth for testing by creating a candidate with an offer token instead.
    
    app_record = sample_interview.application
    app_record.offer_token = "valid_offer_token_123"
    db_session.commit()

    payload = {
        "email": app_record.candidate_email,
        "access_key": "valid_offer_token_123",
        "grievance_type": "technical",
        "description": "My browser crashed during the interview process, please assist."
    }

    resp = client.post("/api/support/ticket", json=payload)
    assert resp.status_code == 200
    
    data = resp.json()
    assert "id" in data
    assert data["issue_type"] == "technical"
    assert "My browser crashed" in data["description"]
    assert "[System Context]" in data["description"]
    assert data["status"] == "pending"
