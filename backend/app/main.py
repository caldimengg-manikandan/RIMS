import os
import sys

# ── Passlib / bcrypt compatibility patch ──────────────────────────────────────
# bcrypt 3.2.x / 4.x breaks passlib 1.7.4 in two ways:
# 1. bcrypt.hashpw raises ValueError if password > 72 bytes (passlib's
#    detect_wrap_bug uses a 73-byte test password).
# 2. bcrypt no longer exposes __about__.__version__; passlib reads this
#    attribute and crashes with AttributeError when loading the backend.
#
# We fix BOTH issues here, BEFORE any app code imports passlib or bcrypt.
import importlib

# Step 1: Add __about__ stub to bcrypt so passlib can read the version.
import bcrypt as _bcrypt_mod
if not hasattr(_bcrypt_mod, "__about__"):
    _bcrypt_mod.__about__ = type("_about", (), {"__version__": _bcrypt_mod.__version__})()

# Step 2: Patch detect_wrap_bug to always return False.
# This function tests whether bcrypt wraps passwords > 72 bytes silently by
# hashing a 73-byte secret. bcrypt 3.2+ correctly raises ValueError instead
# of silently wrapping, so passlib thinks bcrypt is broken. We bypass this.
_ph = importlib.import_module("passlib.handlers.bcrypt")
_ph.detect_wrap_bug = lambda ident: False   # type: ignore[attr-defined]

# Step 3: CryptContext is also imported above; reset its cached backend so it
# reloads with the patched detect_wrap_bug when first used.
try:
    _ph.bcrypt.set_backend("default")  # type: ignore[attr-defined]
except Exception:
    pass  # fine — it'll re-init lazily on first verify
# ──────────────────────────────────────────────────────────────────────────────

# Backend entry-point guard:
if os.getenv("BACKEND_START_MODE") != "script":
    print("Use start.ps1 to run the backend")
    sys.exit(1)

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from app.core.auth import hash_password
from app.core.config import get_settings
from app.infrastructure.database import Base, engine
from app.api import auth, jobs, applications, interviews, decisions, notifications, analytics, tickets, support, hr_tickets, ops_email, settings as hr_settings, onboarding, search
from app.domain.models import (
    User, Job, Application, ResumeExtraction, 
    Interview, InterviewQuestion, InterviewAnswer,
    HiringDecision, Notification,
    ApplicationStage, AuditLog
)
from app.services.interview_engine.websocket_gateway import router as websocket_router

from app.core.logging_config import setup_logging
from app.core.observability import log_json

settings = get_settings()

# Setup structured logging
if os.environ.get("RIMS_LOGGING_DONE", "0") != "1":
    setup_logging(settings.logs_dir, settings.debug)
    os.environ["RIMS_LOGGING_DONE"] = "1"
logger = logging.getLogger(__name__)

# Validate critical settings at startup
settings.validate_config()

# Create tables
Base.metadata.create_all(bind=engine)

# Run startup migrations (add missing columns to existing tables).
# Important: if the server is started with multiple workers (or reload),
# we must avoid running migrations in every worker process.
from app.migrations import run_startup_migrations
if os.environ.get("WORKER_ID", "0") == "0":
    # Uvicorn loads the app from the import string (`app.main:app`) which can
    # cause this module to be evaluated more than once. Ensure migrations
    # only run once per process.
    if os.environ.get("RIMS_STARTUP_MIGRATIONS_DONE", "0") != "1":
        os.environ["RIMS_STARTUP_MIGRATIONS_DONE"] = "1"
        # run_startup_migrations(engine)

# Bootstrap Super Admin from environment variables when no admin exists
from app.infrastructure.database import SessionLocal

def bootstrap_super_admin():
    if not settings.super_admin_email or not settings.super_admin_password:
        logger.info("SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD not configured; skipping Super Admin bootstrap.")
        return

    try:
        from app.infrastructure.database import SessionLocal
        with SessionLocal() as db:
            # Check if any super_admin already exists
            existing_admin = db.query(User).filter(User.role == "super_admin").first()
            if existing_admin:
                logger.info("Super Admin user already exists; skipping bootstrap.")
                return

            existing_email_user = db.query(User).filter(User.email == settings.super_admin_email.lower()).first()
            if existing_email_user:
                logger.warning(
                    f"A user with email {settings.super_admin_email} already exists. Converting to Super Admin."
                )
                existing_email_user.role = "super_admin"
                existing_email_user.is_verified = True
                existing_email_user.is_active = True
                existing_email_user.approval_status = "approved"
                db.commit()
                return

            super_admin = User(
                email=settings.super_admin_email.lower(),
                full_name=settings.super_admin_full_name.strip() or "Super Admin",
                password_hash=hash_password(settings.super_admin_password),
                role="super_admin",
                is_verified=True,
                is_active=True,
                approval_status="approved"
            )
            db.add(super_admin)
            db.commit()
            logger.info(f"Created Super Admin account '{settings.super_admin_email}'.")
    except Exception as e:
        logger.error(f"Super Admin bootstrap failed: {str(e)}")

bootstrap_super_admin()

# Initialize FastAPI app
app = FastAPI(
    title="HR Recruitment System API",
    description="AI-powered automated recruitment platform",
    version="1.0.0",
    redirect_slashes=True
)

import os
from fastapi.staticfiles import StaticFiles
mock_storage_dir = os.path.join(os.getcwd(), "tmp", "mock_storage")
os.makedirs(mock_storage_dir, exist_ok=True)
app.mount("/mock_storage", StaticFiles(directory=mock_storage_dir), name="mock_storage")

import time
app.state.start_time = time.time()

logger.info("Backend running: single worker, no reload, port=10000")

# Wire rate limiter with CORS-aware 429 handler
# slowapi's default handler doesn't include CORS headers, causing browsers to
# report "Failed to fetch" instead of showing the actual "rate limit exceeded" message.
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi import Request as FastAPIRequest
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from app.core.rate_limiter import limiter

def cors_aware_rate_limit_handler(request: FastAPIRequest, exc: RateLimitExceeded):
    """Wrap slowapi's 429 handler to inject CORS headers so browsers can read the error."""
    response = _rate_limit_exceeded_handler(request, exc)
    origin = request.headers.get("origin")
    # For dev, if no origin is found but it's localhost, we can fallback or just allow * for errors
    if not origin and settings.env == "development":
        origin = settings.frontend_base_url
        
    allowed_origins = settings.get_allowed_origins()
    if origin and (origin in allowed_origins or "*" in allowed_origins or settings.env == "development"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cors_aware_rate_limit_handler)

# Ensure essential directories exist
settings.logs_dir.mkdir(parents=True, exist_ok=True)

# Middleware order matters: Starlette applies middleware in reverse-add order,
# so add performance logger first (innermost), CORS last (outermost).
# This ensures CORS headers are always set before the browser sees the response.

# Performance logging middleware — logs slow routes (>500ms)
from app.core.middleware import PerformanceLoggingMiddleware
app.add_middleware(PerformanceLoggingMiddleware)

# CORS middleware — must be outermost so it handles OPTIONS preflights first
allowed_origins = list(set(settings.get_allowed_origins()))
if settings.env == "development":
    allowed_origins = list(set(allowed_origins + ["http://localhost:3000", "http://127.0.0.1:3000"]))
elif "*" in allowed_origins:
    logger.warning("HIGH SECURITY RISK: '*' found in ALLOWED_ORIGINS while ENV=production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    """Lightweight health check with uptime, DB, and rate limiter diagnostics."""
    logger.info("Health check requested")

    # Uptime
    uptime_seconds = round(time.time() - app.state.start_time, 2)

    # DB check (non-blocking)
    db_status = "ok"
    try:
        from sqlalchemy import text
        from app.infrastructure.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "error"

    # Rate limiter check
    rate_limiter_status = "active" if getattr(app.state, "limiter", None) else "inactive"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "uptime_seconds": uptime_seconds,
        "server": "running",
        "port": 10000,
        "workers": 1,
        "database": db_status,
        "rate_limiter": rate_limiter_status,
        "environment": settings.env
    }

# Root endpoint
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "HR Recruitment System API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/auth",
            "jobs": "/api/jobs",
            "applications": "/api/applications",
            "interviews": "/api/interviews",
            "decisions": "/api/decisions",
            "tickets": "/api/tickets"
        }
    }

# Include routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(interviews.router)
app.include_router(decisions.router)
app.include_router(notifications.router)
app.include_router(tickets.router)
app.include_router(support.router)
app.include_router(hr_tickets.router)
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ops_email.router)
app.include_router(hr_settings.router)
app.include_router(onboarding.router)
app.include_router(search.router)
app.include_router(websocket_router)

# Mount local storage for resumes, photos, and ID cards
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Ensure local_storage directory exists
LOCAL_STORAGE_DIR = Path("local_storage")
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/local_storage", StaticFiles(directory=str(LOCAL_STORAGE_DIR)), name="local_storage")

# Error handlers
@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: FastAPIRequest, exc: RequestValidationError):
    """Log validation failures without echoing raw request bodies (PII-safe)."""
    try:
        errs = exc.errors()
        safe_errors = []
        for e in errs[:25]:
            safe_errors.append(
                {
                    "loc": [str(x) for x in (e.get("loc") or ())],
                    "type": e.get("type"),
                    "msg_preview": (str(e.get("msg") or ""))[:120],
                }
            )
        log_json(
            logger,
            "request_validation_failed",
            request_id=request.headers.get("X-Request-ID"),
            endpoint=str(request.url.path),
            status=422,
            level="warning",
            extra={"errors": safe_errors},
        )
    except Exception:
        logger.warning("request_validation_failed (logging error suppressed)")

    response = JSONResponse(status_code=422, content={"detail": exc.errors()})
    origin = request.headers.get("origin")
    allowed_origins = settings.get_allowed_origins()
    if origin and (origin in allowed_origins or "*" in allowed_origins or settings.env == "development"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: FastAPIRequest, exc: HTTPException):
    """Custom HTTP exception handler with CORS support"""
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    
    # Manually add CORS for HTTPExceptions (e.g. 401, 403, 404, 429)
    origin = request.headers.get("origin")
    allowed_origins = settings.get_allowed_origins()
    if origin and (origin in allowed_origins or "*" in allowed_origins or settings.env == "development"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
    return response

from sqlalchemy.exc import SQLAlchemyError

@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: FastAPIRequest, exc: SQLAlchemyError):
    """PII-safe database error handler"""
    logger.error(f"DATABASE ERROR: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "A database error occurred. The support team has been notified.",
            "error_type": "database_error"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: FastAPIRequest, exc: Exception):
    import traceback
    error_msg = f"INTERNAL SERVER ERROR: {str(exc)}\n{traceback.format_exc()}"
    logger.error(error_msg)
    
    detail = str(exc) if settings.debug else "An unexpected internal server error occurred."
    response = JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "error_type": "internal_error"
        }
    )
    
    # Manually add CORS for 500 errors since they might bypass middleware if they crash early
    origin = request.headers.get("origin")
    allowed_origins = settings.get_allowed_origins()
    if origin and (origin in allowed_origins or "*" in allowed_origins or settings.env == "development"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
    return response


#
# Note:
# This module must NOT start a server itself.
# Entrypoint is enforced via `start.ps1` and `BACKEND_START_MODE=script`.
