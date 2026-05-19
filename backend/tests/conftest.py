"""
conftest.py — Shared test fixtures for RIMS backend unit tests.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet
import sqlalchemy
from sqlalchemy.pool import StaticPool

# ──────────────────────────────────────────────────────────────────────────────
# 1.  SQLAlchemy engine patching (MUST BE FIRST, BEFORE ANY APP IMPORTS)
# ──────────────────────────────────────────────────────────────────────────────

original_create_engine = sqlalchemy.create_engine

def mocked_create_engine(*args, **kwargs):
    if args and args[0].startswith("sqlite"):
        kwargs.pop("pool_size", None)
        kwargs.pop("max_overflow", None)
        kwargs.pop("pool_recycle", None)
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = kwargs.get("connect_args", {})
        kwargs["connect_args"]["check_same_thread"] = False
    return original_create_engine(*args, **kwargs)

sqlalchemy.create_engine = mocked_create_engine

# ──────────────────────────────────────────────────────────────────────────────
# 2.  Environment Bootstrap
# ──────────────────────────────────────────────────────────────────────────────

# Disable dotenv loading during tests to prevent overriding our test env vars
with patch("dotenv.load_dotenv", return_value=None):
    import app.core.config as config
    # Clear any cached settings if they were already loaded
    config.get_settings.cache_clear()

_TEST_FERNET_KEY = Fernet.generate_key().decode()
_TEST_JWT_SECRET = "test-jwt-secret-for-unit-tests"

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET"] = _TEST_JWT_SECRET
os.environ["ENCRYPTION_KEY"] = _TEST_FERNET_KEY
os.environ["BACKEND_START_MODE"] = "script"
os.environ["ENV"] = "test"
os.environ["SUPABASE_URL"] = "https://fake.supabase.co"
os.environ["SUPABASE_KEY"] = "fake-supabase-key"
os.environ["GROQ_API_KEY"] = "gsk_fake_groq_key"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:3000"

# Clear settings cache again to ensure test environment is picked up
config.get_settings.cache_clear()
TEST_SETTINGS = config.get_settings()

# Now import modules and propagate settings
import app.core.auth
app.core.auth.settings = TEST_SETTINGS

import app.api.auth
app.api.auth.settings = TEST_SETTINGS

import app.api.interviews
app.api.interviews.settings = TEST_SETTINGS

import app.main
app.main.settings = TEST_SETTINGS

async def dummy_imap_polling_loop():
    pass
app.main.imap_polling_loop = dummy_imap_polling_loop

# Now import the app's database module — it will use our mocked_create_engine
import app.infrastructure.database as db_mod
from app.infrastructure.database import Base, engine, SessionLocal

# Ensure the engine is indeed using StaticPool
if not isinstance(engine.pool, StaticPool):
    from sqlalchemy import create_engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_mod.engine = engine
    db_mod.SessionLocal = sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)

TEST_ENGINE = engine
TestSessionLocal = db_mod.SessionLocal

# ──────────────────────────────────────────────────────────────────────────────
# 3.  Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_database():
    import app.domain.models  # noqa: F401
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

@pytest.fixture()
def db_session(setup_database):
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.infrastructure.database import get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()

# ──────────────────────────────────────────────────────────────────────────────
# 4.  Model Factories
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_hr_user(db_session):
    from app.domain.models import User
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        email="hr@testcompany.com",
        password_hash=pwd_ctx.hash("HrPassword1!"),
        full_name="Test HR Manager",
        role="hr",
        is_active=True,
        is_verified=True,
        approval_status="approved",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture()
def sample_candidate_user(db_session):
    from app.domain.models import User
    from passlib.context import CryptContext
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = User(
        email="candidate@example.com",
        password_hash=pwd_ctx.hash("CandPassword1!"),
        full_name="Test Candidate",
        role="candidate",
        is_active=True,
        is_verified=True,
        approval_status="approved",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture()
def sample_job(db_session, sample_hr_user):
    from app.domain.models import Job
    job = Job(
        title="Software Engineer",
        description="Build and maintain scalable web applications.",
        experience_level="mid",
        location="Remote",
        status="open",
        hr_id=sample_hr_user.id,
        aptitude_enabled=False,
        first_level_enabled=True,
        duration_minutes=60,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job

@pytest.fixture()
def sample_application(db_session, sample_job):
    from app.domain.models import Application
    app_record = Application(
        job_id=sample_job.id,
        hr_id=sample_job.hr_id,
        candidate_name="Jane Applicant",
        candidate_email="jane@example.com",
        resume_file_name="jane_resume.pdf",
        resume_file_path="/resumes/jane_resume.pdf",
        status="applied",
        resume_status="parsed",
        resume_score=75.0,
    )
    db_session.add(app_record)
    db_session.commit()
    db_session.refresh(app_record)
    return app_record

@pytest.fixture()
def sample_interview(db_session, sample_application):
    from app.domain.models import Interview
    interview = Interview(
        application_id=sample_application.id,
        status="not_started",
        total_questions=10,
        questions_asked=0,
        interview_stage="first_level",
        duration_minutes=60,
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    return interview

# ──────────────────────────────────────────────────────────────────────────────
# 5.  Auth Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_token(user_id: int, role: str) -> str:
    from jose import jwt
    import datetime
    from app.core.config import get_settings
    settings = get_settings()
    
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    # Use the secret FROM settings to ensure consistency
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

@pytest.fixture()
def hr_auth_headers(sample_hr_user):
    token = _make_token(sample_hr_user.id, "hr")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
def candidate_auth_headers(sample_candidate_user):
    token = _make_token(sample_candidate_user.id, "candidate")
    return {"Authorization": f"Bearer {token}"}
