from supabase import create_client, Client
from app.core.config import get_settings
from app.core.observability import log_json
import logging
from typing import Optional

logger = logging.getLogger(__name__)
settings = get_settings()

def get_supabase_client() -> Optional[Client]:
    """Initialize Supabase client from settings."""
    if not settings.supabase_url or not settings.supabase_key:
        logger.warning("Supabase URL or Key not configured. Storage operations will fail.")
        return None
    try:
        # Client initialization is cheap in supabase-py as it's just a wrapper
        return create_client(settings.supabase_url, settings.supabase_key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

def upload_file(bucket: str, path: str, content: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
    """
    Upload file content to a Supabase bucket.
    Returns the storage path on success.
    """
    supabase = get_supabase_client()
    if not supabase:
        logger.error("Storage failed: Supabase client not initialized")
        return None
        
    # File Corruption & Stress Validation (Harden bandwidth)
    size_mb = len(content) / (1024 * 1024)
    if len(content) == 0:
        log_json(logger, "storage_upload_failed", level="warning", extra={"bucket": bucket, "path": path, "error": "Attempted to upload 0-byte file."})
        return None
    if size_mb > 50:
        log_json(logger, "storage_upload_failed", level="warning", extra={"bucket": bucket, "path": path, "error": f"File too large: {size_mb:.2f} MB"})
        return None
    
    try:
        res = supabase.storage.from_(bucket).upload(
            path=path,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        # Handle dict or object response based on supabase-py version
        if isinstance(res, dict):
            return res.get("path") or path
        return getattr(res, "path", path)
    except Exception as e:
        log_json(logger, "storage_upload_failed", level="error", extra={"bucket": bucket, "path": path, "error": str(e)})
        return None

def delete_file(bucket: str, path: str):
    """Delete a file from Supabase bucket."""
    supabase = get_supabase_client()
    if not supabase:
        return None
    try:
        return supabase.storage.from_(bucket).remove([path])
    except Exception as e:
        logger.error(f"Failed to delete {path} from {bucket}: {e}")
        return None

def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> Optional[str]:
    """Generate a signed URL for private access."""
    supabase = get_supabase_client()
    if not supabase:
        return None
    try:
        # Storage V2 client returns a signed URL string directly or a dict depending on version
        res = supabase.storage.from_(bucket).create_signed_url(path, expires_in)
        if isinstance(res, dict):
            return res.get("signedURL") or res.get("signedUrl")
        return res
    except Exception as e:
        logger.error(f"Error generating signed URL for {path} in {bucket}: {e}")
        return None

def get_public_url(bucket: str, path: str) -> Optional[str]:
    """Generate a public URL for public buckets."""
    supabase = get_supabase_client()
    if not supabase:
        return None
    try:
        return supabase.storage.from_(bucket).get_public_url(path)
    except Exception as e:
        logger.error(f"Error generating public URL for {path} in {bucket}: {e}")
        return None
