import logging
from typing import Optional, Any
from app.core.config import get_settings
from app.core.observability import log_json

logger = logging.getLogger(__name__)
settings = get_settings()

class MockStorageBucket:
    """Mock for supabase.storage.from_(bucket)"""
    def upload(self, path: str, file: Any, file_options: dict = None) -> dict:
        return {"path": path}
    
    def remove(self, paths: list) -> list:
        return paths
        
    def create_signed_url(self, path: str, expires_in: int) -> str:
        return f"https://mock-storage.local/{path}?token=mock"
        
    def get_public_url(self, path: str) -> str:
        return f"https://mock-storage.local/public/{path}"
    
    def download(self, path: str) -> Optional[bytes]:
        # Return a realistic resume text to make AI analysis "work" meaningfully during testing
        resume_text = """
        JOHN DOE
        Senior Software Engineer
        Email: john.doe@example.com | Phone: +1-555-0199
        
        SUMMARY:
        Results-oriented Software Engineer with 8 years of experience in building scalable web applications 
        using Python, FastAPI, and React. Proven track record of improving system performance by 40%.
        
        SKILLS:
        - Languages: Python, JavaScript, TypeScript, SQL
        - Frameworks: FastAPI, Django, React, Next.js
        - Tools: Docker, Kubernetes, AWS, PostgreSQL, Git
        
        EXPERIENCE:
        TechCorp Inc. | Senior Software Engineer | 2018 - Present
        - Led a team of 5 engineers to migrate legacy monolith to microservices.
        - Optimized database queries, reducing latency by 200ms.
        
        EDUCATION:
        Bachelor of Science in Computer Science | University of Technology
        """
        return resume_text.encode('utf-8')

class MockSupabaseClient:
    """Mock for Supabase client to prevent AttributeErrors in calling modules."""
    def __init__(self):
        self.storage = self
        
    def from_(self, bucket: str) -> MockStorageBucket:
        return MockStorageBucket()

def get_supabase_client() -> Optional[Any]:
    """Return a mock client to satisfy existing code paths without the supabase library."""
    return MockSupabaseClient()

def upload_file(bucket: str, path: str, content: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
    """
    MOCK: Simulate file upload to a bucket.
    Returns the path as if it was successfully uploaded.
    """
    # Still perform size validation to maintain existing logic behavior
    size_mb = len(content) / (1024 * 1024)
    if len(content) == 0:
        log_json(logger, "storage_upload_mock_skipped", level="warning", extra={"bucket": bucket, "path": path, "error": "0-byte file"})
        return None
    if size_mb > 50:
        log_json(logger, "storage_upload_mock_skipped", level="warning", extra={"bucket": bucket, "path": path, "error": "File too large"})
        return None
    
    logger.info(f"MOCK STORAGE: Uploaded {len(content)} bytes to {bucket}/{path}")
    return path

def delete_file(bucket: str, path: str):
    """MOCK: Simulate file deletion."""
    logger.info(f"MOCK STORAGE: Deleted {path} from {bucket}")
    return [path]

def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> Optional[str]:
    """MOCK: Generate a placeholder signed URL."""
    if not path:
        return None
    return f"https://mock-storage.local/{bucket}/{path}?expires={expires_in}"

def get_public_url(bucket: str, path: str) -> Optional[str]:
    """MOCK: Generate a placeholder public URL."""
    if not path:
        return None
    return f"https://mock-storage.local/public/{bucket}/{path}"
