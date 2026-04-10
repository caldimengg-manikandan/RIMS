from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache
from typing import List
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Project root (backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment-specific dotenv loading (non-breaking).
# Precedence rules:
# 1) Load env-specific file first (if present) so it can override base defaults.
# 2) Load `.env` afterwards (if present) to fill any missing vars.
# 3) Never override real OS environment variables.
_active_env = (os.getenv("ENV") or "development").strip().lower()
_env_specific = ".env.production" if _active_env == "production" else ".env.local"
_env_specific_path = os.path.join(str(BASE_DIR), _env_specific)
_base_env_path = os.path.join(str(BASE_DIR), ".env")
if os.path.exists(_env_specific_path):
    load_dotenv(_env_specific_path, override=False)
if os.path.exists(_base_env_path):
    load_dotenv(_base_env_path, override=False)

class Settings(BaseSettings):
    base_dir: Path = BASE_DIR
    logs_dir: Path = BASE_DIR / "logs"
    uploads_dir: Path = BASE_DIR / "uploads"
    # Database
    # To use PostgreSQL, add this to your .env file:
    # DATABASE_URL=postgresql://user:password@host:port/dbname
    database_url: str = "" # Mandatory via validate_config
    videos_dir: Path = BASE_DIR / "uploads" / "videos"


    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 120
    jwt_refresh_expiration_days: int = 7

    # OpenAI
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # Encryption
    encryption_key: str = ""

    # Internal lists for rotation
    @property
    def openai_keys(self) -> List[str]:
        return [k.strip() for k in self.openai_api_key.split(",") if k.strip()]

    @property
    def deepseek_keys(self) -> List[str]:
        return [k.strip() for k in self.deepseek_api_key.split(",") if k.strip()]

    @property
    def gemini_keys(self) -> List[str]:
        return [k.strip() for k in self.gemini_api_key.split(",") if k.strip()]

    @property
    def anthropic_keys(self) -> List[str]:
        return [k.strip() for k in self.anthropic_api_key.split(",") if k.strip()]

    @property
    def groq_keys(self) -> List[str]:
        return [k.strip() for k in self.groq_api_key.split(",") if k.strip()]

    # SMTP Email Configuration
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    
    # Resend API
    resend_api_key: str = ""
    # Optional override for the "from" address used by Resend.
    # If empty, we fall back to SMTP_FROM / SMTP_USER for convenience.
    resend_from: str = ""
    
    # Brevo API
    brevo_api_key: str = ""

    # Super Admin bootstrap (optional, auto-created at startup)
    super_admin_email: str = ""
    super_admin_password: str = ""
    super_admin_full_name: str = "Super Admin"
    allowed_origins: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3001,http://127.0.0.1:3002"

    # Server
    host: str = "0.0.0.0"
    port: int = 10000  # Default to 10000 for Render
    debug: bool = False
    env: str = "development"
    ws_enforce_interview_jwt: bool = False
    enable_request_id_idempotency: bool = True
    # redis://host:6379/0 — shared idempotency + X-Request-ID replay across workers
    redis_url: str = ""
    # Clamp idempotency marker + ephemeral replay TTLs (seconds); Redis and in-memory fallback both honor this band.
    idempotency_ttl_min_seconds: int = 60
    idempotency_ttl_max_seconds: int = 120
    ai_observability_enabled: bool = True
    # A007: Use env var as-is (no auto replacement from ALLOWED_ORIGINS)
    # Supabase Storage
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket_resumes: str = "resumes"
    supabase_bucket_offers: str = "offers"
    supabase_bucket_id_cards: str = "id-cards"
    supabase_bucket_id_photos: str = "id-photos"
    supabase_bucket_videos: str = "videos"

    frontend_base_url: str = os.getenv(
        "NEXT_PUBLIC_FRONTEND_URL",
        os.getenv(
            "FRONTEND_URL",
            os.getenv(
                "NEXT_PUBLIC_APP_URL",
                os.getenv("FRONTEND_BASE_URL", "http://localhost:3000"),
            ),
        ),
    )

    class Config:
        env_file = os.path.join(str(BASE_DIR), ".env")
        case_sensitive = False
        extra = "ignore"

    @model_validator(mode="after")
    def _enforce_ws_jwt_in_production(self):
        """Standardize and validate configuration values."""
        # Standardize Supabase Key (Map service_role to generic key if missing)
        if not self.supabase_key and self.supabase_service_role_key:
            object.__setattr__(self, "supabase_key", self.supabase_service_role_key)

        # Normalize common email-provider inputs early to avoid subtle auth/config bugs.
        try:
            object.__setattr__(self, "smtp_host", (self.smtp_host or "").strip())
            object.__setattr__(self, "smtp_user", (self.smtp_user or "").strip())
            # Gmail "App Passwords" are often pasted with spaces; SMTP AUTH requires the raw token.
            object.__setattr__(self, "smtp_password", (self.smtp_password or "").strip())
            object.__setattr__(self, "smtp_from", (self.smtp_from or "").strip())
            object.__setattr__(self, "resend_api_key", (self.resend_api_key or "").strip())
            object.__setattr__(self, "resend_from", (self.resend_from or "").strip())
        except Exception:
            pass

        explicit = os.environ.get("WS_ENFORCE_INTERVIEW_JWT")
        if explicit is not None:
            return self
        if (self.env or "").strip().lower() == "production":
            object.__setattr__(self, "ws_enforce_interview_jwt", True)
        return self

    def get_allowed_origins(self) -> List[str]:
        """Convert comma-separated string to list, with safety fallbacks"""
        origins = [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        
        # If in development and no origins are set or only localhost, 
        # consider allowing * for easier debugging, but keep default strict for production.
        if self.env == "development" and ("*" not in origins):
            # We don't force * here to keep it secure by default, 
            # but main.py's exception handlers already check self.env.
            pass
            
        return origins

    def validate_config(self):
        """Validate critical settings at startup. Called from main.py."""
        import logging
        logger = logging.getLogger(__name__)

        # 1. Mandatory Critical Settings (All Environments)
        critical_required = {
            "DATABASE_URL": self.database_url,
            "JWT_SECRET": self.jwt_secret,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_KEY": self.supabase_key,
            "GROQ_API_KEY": self.groq_api_key,
        }
        missing_critical = [k for k, v in critical_required.items() if not v or v == ""]
        
        if missing_critical:
            error_msg = (
                f"CRITICAL STARTUP ERROR: Missing mandatory environment variables: {', '.join(missing_critical)}. "
                "The server cannot start. Please check your .env file."
            )
            logger.critical(error_msg)
            # Only blow up if not in development OR if it's REALLY missing
            if self.env == "production" or not self.database_url:
                raise ValueError(error_msg)
            else:
                logger.warning("DEVELOPMENT MODE: Proceeding with missing/mocked critical settings.")

        # 2. Production-Only Strict Mode
        if self.env == "production":
            if self.debug:
                raise ValueError("SECURITY ERROR: 'DEBUG=true' is not allowed in production.")
            
            # CORS safety check
            if "localhost" in self.allowed_origins or "*" in self.allowed_origins:
                logger.warning("SECURITY WARNING: Permissive CORS found in production (localhost/*).")

        # 3. Functional Warnings (Non-blocking)
        optional_warnings = {
            "ENCRYPTION_KEY": self.encryption_key,
        }
        for k, v in optional_warnings.items():
            if not v or v == "":
                logger.warning(f"CONFIG WARNING: '{k}' is missing. Some features (encryption) will be degraded.")

        # Email provider check
        smtp_configured = bool(self.smtp_host and self.smtp_user and self.smtp_password)
        resend_configured = bool(self.resend_api_key)
        if not smtp_configured and not resend_configured:
            logger.warning("CONFIG WARNING: No email provider (SMTP/Resend) configured. Notifications will fail.")

        # A007: In production, warn if we detect localhost URLs but do not change them.
        # This keeps behavior stable and ensures deployment can control correctness via env vars.
        if self.env == "production":
            if "localhost" in self.frontend_base_url or "127.0.0.1" in self.frontend_base_url:
                import logging
                logging.getLogger(__name__).warning(
                    "WARNING: frontend_base_url appears to be localhost while ENV=production. "
                    "Check NEXT_PUBLIC_FRONTEND_URL / FRONTEND_BASE_URL in your environment."
                )

        # Additive logging: active environment and resolved URLs.
        try:
            api_base_url = os.getenv("NEXT_PUBLIC_API_BASE_URL", "")
            resolved_origins = self.get_allowed_origins()
            logging.getLogger(__name__).info(
                "Environment config",
                extra={
                    "env": self.env,
                    "frontend_base_url": self.frontend_base_url,
                    "api_base_url": api_base_url,
                    "allowed_origins": resolved_origins,
                },
            )
        except Exception:
            pass

@lru_cache()
def get_settings():
    return Settings()
