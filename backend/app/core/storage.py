import logging
import os
from pathlib import Path
from typing import Optional, Any, List
from app.core.config import get_settings
from app.core.observability import log_json

logger = logging.getLogger(__name__)
settings = get_settings()

# Define buckets that should be stored locally (empty by default to use Supabase Cloud)
LOCAL_BUCKETS = set()

# Local storage configuration
LOCAL_STORAGE_BASE = Path("local_storage")
LOCAL_STORAGE_BASE.mkdir(parents=True, exist_ok=True)

def _get_local_path(bucket: str, path: str) -> Path:
    """
    Generate a local path using the format: <file_type>_<filename>
    Sanitize the path by replacing slashes with underscores.
    """
    safe_name = path.replace("/", "_").replace("\\", "_")
    return LOCAL_STORAGE_BASE / f"{bucket}_{safe_name}"

def _get_local_url(bucket: str, path: str) -> str:
    """Generate a URL for the locally stored file."""
    api_base_url = os.getenv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:10000").rstrip("/")
    safe_name = path.replace("/", "_").replace("\\", "_")
    return f"{api_base_url}/local_storage/{bucket}_{safe_name}"

# --- Proxy Logic for direct Supabase client usage transparency ---

class LocalBucketProxy:
    """Mimics Supabase storage bucket interface for local files."""
    def __init__(self, bucket: str):
        self.bucket = bucket

    def upload(self, path: str, content: bytes, options: dict = None) -> dict:
        upload_file(self.bucket, path, content)
        return {"path": path}

    def download(self, path: str) -> bytes:
        data = download_file(self.bucket, path)
        if data is None:
            raise Exception(f"File not found in local storage: {self.bucket}/{path}")
        return data

    def remove(self, paths: List[str]) -> List[str]:
        for p in paths:
            delete_file(self.bucket, p)
        return paths

    def create_signed_url(self, path: str, expires_in: int) -> str:
        return get_signed_url(self.bucket, path, expires_in) or ""

    def get_public_url(self, path: str) -> str:
        return get_public_url(self.bucket, path) or ""

class SupabaseStorageProxy:
    """Mimics Supabase storage client interface."""
    def __init__(self, real_storage=None):
        self.real_storage = real_storage

    def from_(self, bucket: str):
        if bucket in LOCAL_BUCKETS:
            return LocalBucketProxy(bucket)
        if self.real_storage:
            return self.real_storage.from_(bucket)
        raise Exception(f"Supabase storage not configured for bucket: {bucket}")

class SupabaseClientProxy:
    """Mimics Supabase client for transparency."""
    def __init__(self, real_client=None):
        self.storage = SupabaseStorageProxy(real_client.storage if real_client else None)

# --- Supabase Logic Integration ---

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

def get_supabase_client() -> Optional[Any]:
    """
    Returns a Proxy that transparently handles Local or Supabase storage.
    Ensures existing code calling `get_supabase_client().storage.from_()...` continues to work.
    """
    real_client = None
    if settings.supabase_url and settings.supabase_key and SUPABASE_AVAILABLE:
        try:
            real_client = create_client(settings.supabase_url, settings.supabase_key)
        except Exception as e:
            logger.error(f"Failed to initialize real Supabase client: {e}")
    
    # Always return a proxy so that LOCAL_BUCKETS are caught even if Supabase is offline/unconfigured
    return SupabaseClientProxy(real_client)

# --- Top-level Storage API ---

def upload_file(bucket: str, path: str, content: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
    """
    Dual-Write Strategy: Uploads the file to BOTH Local Storage and Supabase Cloud.
    Returns the Supabase path if successful, or local path as fallback.
    """
    success_flags = []

    # 1. Attempt Local Write (for backup/fast access)
    try:
        local_file_path = _get_local_path(bucket, path)
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_file_path, "wb") as f:
            f.write(content)
        logger.info(f"STORAGE: Saved local copy to {local_file_path}")
        success_flags.append("local")
    except Exception as e:
        logger.warning(f"STORAGE: Local backup failed for {bucket}/{path}: {e}")

    # 2. Attempt Supabase Upload (for cloud persistence)
    proxy = get_supabase_client()
    if proxy and proxy.storage.real_storage:
        try:
            proxy.storage.real_storage.from_(bucket).upload(
                path, 
                content, 
                {"content-type": content_type, "upsert": "true"}
            )
            logger.info(f"STORAGE: Uploaded to Supabase bucket: {bucket}")
            success_flags.append("cloud")
        except Exception as e:
            logger.error(f"STORAGE: Supabase upload failed for {bucket}/{path}: {e}")

    # Return success indicator (prefer path if at least one succeeded)
    if not success_flags:
        return None
    
    logger.info(f"MOCK STORAGE: Uploaded {len(content)} bytes to {bucket}/{path}")
    return path

def download_file(bucket: str, path: str) -> Optional[bytes]:
    """
    Hybrid Download Strategy: Prefers Local Storage (fast), fallbacks to Supabase (cloud).
    """
    # 1. Try Local First
    local_file_path = _get_local_path(bucket, path)
    if local_file_path.exists():
        try:
            with open(local_file_path, "rb") as f:
                logger.debug(f"STORAGE: Cache hit (local) for {bucket}/{path}")
                return f.read()
        except Exception as e:
            logger.warning(f"STORAGE: Failed to read local copy: {e}")

    # 2. Fallback to Supabase
    proxy = get_supabase_client()
    if proxy and proxy.storage.real_storage:
        try:
            logger.info(f"STORAGE: Fetching from cloud for {bucket}/{path}")
            return proxy.storage.real_storage.from_(bucket).download(path)
        except Exception as e:
            logger.error(f"STORAGE: Cloud download failed for {bucket}/{path}: {e}")
            return None
            
    return None

def delete_file(bucket: str, path: str):
    """
    Delete a file from BOTH local storage and Supabase.
    """
    # 1. Delete Local
    local_file_path = _get_local_path(bucket, path)
    if local_file_path.exists():
        try:
            os.remove(local_file_path)
            logger.info(f"STORAGE: Deleted local copy of {bucket}/{path}")
        except Exception as e:
            logger.warning(f"STORAGE: Failed to delete local copy: {e}")

    # 2. Delete Supabase
    proxy = get_supabase_client()
    if proxy and proxy.storage.real_storage:
        try:
            return proxy.storage.real_storage.from_(bucket).remove([path])
        except Exception:
            return []
    return []

def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> Optional[str]:
    """
    Get a URL. Prefers Supabase signed URL for cloud accessibility, 
    but provides a local API link if cloud is unavailable and file exists locally.
    """
    if not path:
        return None
        
    proxy = get_supabase_client()
    if proxy and proxy.storage.real_storage:
        try:
            res = proxy.storage.real_storage.from_(bucket).create_signed_url(path, expires_in)
            if isinstance(res, dict):
                return res.get("signedURL") or res.get("signedUrl")
            elif isinstance(res, str):
                return res
        except Exception as e:
            logger.warning(f"STORAGE: Failed to get signed URL from cloud: {e}")
            
    return _get_local_url(bucket, path)

def get_public_url(bucket: str, path: str) -> Optional[str]:
    """
    Get a public URL. Local files return a static FastAPI URL.
    """
    if not path:
        return None
        
    proxy = get_supabase_client()
    if proxy and proxy.storage.real_storage:
        try:
            res = proxy.storage.real_storage.from_(bucket).get_public_url(path)
            if isinstance(res, str):
                return res
        except Exception as e:
            logger.warning(f"STORAGE: Failed to get public URL from cloud: {e}")
    
    return _get_local_url(bucket, path)
