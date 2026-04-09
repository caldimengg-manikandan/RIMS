import logging
import os
from pathlib import Path
from typing import Optional, Any, List
from app.core.config import get_settings
from app.core.observability import log_json

logger = logging.getLogger(__name__)
settings = get_settings()

# Define buckets that should be stored locally
LOCAL_BUCKETS = {
    settings.supabase_bucket_resumes,
    settings.supabase_bucket_id_photos,
    settings.supabase_bucket_id_cards
}

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
    Upload a file. RESUMES, PHOTOS, and ID CARDS are stored LOCALLY.
    Others go to Supabase.
    """
    if bucket in LOCAL_BUCKETS:
        try:
            local_file_path = _get_local_path(bucket, path)
            with open(local_file_path, "wb") as f:
                f.write(content)
            logger.info(f"LOCAL STORAGE: Saved {bucket} to {local_file_path}")
            return path
        except Exception as e:
            logger.error(f"Failed local upload to {bucket}/{path}: {e}")
            return None
    
    # Supabase fallback
    proxy = get_supabase_client()
    if not proxy or not proxy.storage.real_storage:
        logger.warning(f"Supabase not configured for cloud-only bucket: {bucket}")
        return None
    
    try:
        proxy.storage.real_storage.from_(bucket).upload(path, content, {"content-type": content_type, "upsert": "true"})
        return path
    except Exception as e:
        logger.error(f"Supabase upload failed for {bucket}/{path}: {e}")
        return None

def download_file(bucket: str, path: str) -> Optional[bytes]:
    """
    Download a file from local storage or Supabase.
    """
    if bucket in LOCAL_BUCKETS:
        local_file_path = _get_local_path(bucket, path)
        if local_file_path.exists():
            try:
                with open(local_file_path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read local file {local_file_path}: {e}")
                return None
        return None

    # Supabase fallback
    proxy = get_supabase_client()
    if not proxy or not proxy.storage.real_storage:
        return None
    
    try:
        return proxy.storage.real_storage.from_(bucket).download(path)
    except Exception as e:
        logger.error(f"Supabase download failed for {bucket}/{path}: {e}")
        return None

def delete_file(bucket: str, path: str):
    """
    Delete a file from local storage or Supabase.
    """
    if bucket in LOCAL_BUCKETS:
        local_file_path = _get_local_path(bucket, path)
        if local_file_path.exists():
            try:
                os.remove(local_file_path)
                logger.info(f"LOCAL STORAGE: Deleted {local_file_path}")
                return [path]
            except Exception:
                return []
        return []

    # Supabase fallback
    proxy = get_supabase_client()
    if not proxy or not proxy.storage.real_storage:
        return []
    
    try:
        return proxy.storage.real_storage.from_(bucket).remove([path])
    except Exception:
        return []

def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> Optional[str]:
    """
    Get a URL. Local files return a static FastAPI URL. Others return Supabase signed URL.
    """
    if not path:
        return None
        
    if bucket in LOCAL_BUCKETS:
        return _get_local_url(bucket, path)

    # Supabase fallback
    proxy = get_supabase_client()
    if not proxy or not proxy.storage.real_storage:
        return None
    
    try:
        res = proxy.storage.real_storage.from_(bucket).create_signed_url(path, expires_in)
        if isinstance(res, dict) and "signedURL" in res:
             return res["signedURL"]
        return str(res)
    except Exception:
        return None

def get_public_url(bucket: str, path: str) -> Optional[str]:
    """
    Get a public URL. Local files return a static FastAPI URL.
    """
    if not path:
        return None
        
    if bucket in LOCAL_BUCKETS:
        return _get_local_url(bucket, path)

    # Supabase fallback
    proxy = get_supabase_client()
    if not proxy or not proxy.storage.real_storage:
        return None
    
    try:
        return proxy.storage.real_storage.from_(bucket).get_public_url(path)
    except Exception:
        return None
