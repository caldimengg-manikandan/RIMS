from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os
from pathlib import Path

# Project root (backend folder)
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    base_dir: Path = BASE_DIR
    logs_dir: Path = BASE_DIR / "logs"
    uploads_dir: Path = BASE_DIR / "uploads"
    videos_dir: Path = BASE_DIR / "uploads" / "videos"
    # Database
    # To use PostgreSQL, add this to your .env file:
    # DATABASE_URL=postgresql://user:password@host:port/dbname
    database_url: str = f"sqlite:///{BASE_DIR}/sql_app.db"

    # JWT
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
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

    # CORS - parse as comma-separated string from env
    allowed_origins: str = "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3001,http://127.0.0.1:3002"

    # Server
    host: str = "0.0.0.0"
    port: int = 10000  # Default to 10000 for Render
    debug: bool = False
    env: str = "development"
    frontend_base_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_allowed_origins(self) -> List[str]:
        """Convert comma-separated string to list"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def validate_production_settings(self):
        """Validate critical settings at startup. Called from main.py."""
        if not self.jwt_secret:
            raise ValueError(
                "CRITICAL ERROR: 'JWT_SECRET' environment variable is not set. "
                "The server cannot start without a secret key for authentication. "
                "Please add JWT_SECRET to your environment variables or .env file."
            )
        if not self.encryption_key:
            raise ValueError(
                "CRITICAL ERROR: 'ENCRYPTION_KEY' environment variable is not set. "
                "The server cannot start without a key for data encryption. "
                "Please add ENCRYPTION_KEY to your environment variables or .env file."
            )
        if self.debug and self.env == "production":
            raise ValueError(
                "CRITICAL ERROR: 'DEBUG=true' is not allowed when 'ENV=production'. "
                "Please set 'DEBUG=false' for your production environment."
            )
        
        # CORS safety check for production
        if self.env == "production" and "localhost" in self.allowed_origins:
            # We don't raise error but we should at least log it or warn
            # For now, let's be strict as requested by Task 7 "restrict to frontend domain only"
            print("WARNING: 'localhost' found in ALLOWED_ORIGINS while ENV=production. "
                  "Ensure CORS is restricted to your production domain.")

@lru_cache()
def get_settings():
    return Settings()
