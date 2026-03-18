from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.core.config import get_settings
from app.infrastructure.database import Base, engine
from app.api import auth, jobs, applications, interviews, decisions, notifications, analytics, tickets
from app.domain.models import (
    User, Job, Application, ResumeExtraction, 
    Interview, InterviewQuestion, InterviewAnswer,
    HiringDecision, Notification,
    ApplicationStage, AuditLog
)
from app.services.interview_engine.websocket_gateway import router as websocket_router

from app.core.logging_config import setup_logging

settings = get_settings()

# Setup structured logging
setup_logging(settings.logs_dir, settings.debug)

# Validate production-critical settings at startup
settings.validate_production_settings()

# Create tables
Base.metadata.create_all(bind=engine)

# Run startup migrations (add missing columns to existing tables)
# from app.core.migrations import run_startup_migrations
# run_startup_migrations(engine)

# Initialize FastAPI app
app = FastAPI(
    title="HR Recruitment System API",
    description="AI-powered automated recruitment platform",
    version="1.0.0",
    redirect_slashes=True
)

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
        origin = "http://localhost:3000"
        
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
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
settings.videos_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)

# Static files (Resume Uploads)
app.mount("/uploads", StaticFiles(directory=str(settings.uploads_dir)), name="uploads")
app.mount("/uploads/videos", StaticFiles(directory=str(settings.videos_dir)), name="videos")

# Middleware order matters: Starlette applies middleware in reverse-add order,
# so add performance logger first (innermost), CORS last (outermost).
# This ensures CORS headers are always set before the browser sees the response.

# Performance logging middleware — logs slow routes (>500ms)
from app.core.middleware import PerformanceLoggingMiddleware
app.add_middleware(PerformanceLoggingMiddleware)

# CORS middleware — must be outermost so it handles OPTIONS preflights first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "HR Recruitment API is running"}

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
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(websocket_router)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: FastAPIRequest, exc: Exception):
    import traceback
    traceback.print_exc()
    detail = f"Internal server error: {str(exc)}" if settings.debug else "Internal server error"
    response = JSONResponse(status_code=500, content={"detail": detail})
    
    # Manually add CORS for 500 errors since they might bypass middleware if they crash early
    origin = request.headers.get("origin")
    allowed_origins = settings.get_allowed_origins()
    if origin and (origin in allowed_origins or "*" in allowed_origins or settings.env == "development"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
    return response


if __name__ == "__main__":
    import uvicorn
    # Log the startup configuration for easier debugging of Render deployments
    print(f"Starting server on {settings.host}:{settings.port} (ENV={settings.env}, DEBUG={settings.debug})")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

