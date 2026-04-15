import hashlib
import os
from typing import Optional, Tuple


def get_resume_extension(filename: Optional[str]) -> str:
    """
    Extract and normalize resume extension without trusting client.
    Returns lowercase extension including leading dot, e.g. ".pdf".
    """
    name = filename or ""
    _, ext = os.path.splitext(name)
    return ext.lower()


def validate_resume_signature(resume_ext: str, content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Basic signature validation to prevent trivial spoofing.
    Non-breaking: if content is empty or signature mismatch, returns (False, reason).
    """
    if not content:
        return False, "empty_content"
    if resume_ext == ".pdf" and not content.startswith(b"%PDF"):
        return False, "invalid_pdf_signature"
    if resume_ext == ".docx" and not content.startswith(b"PK"):
        return False, "invalid_docx_signature"
    if resume_ext == ".doc" and not content.startswith(b"\xd0\xcf\x11\xe0"):
        return False, "invalid_doc_signature"
    return True, None


def generate_hashed_resume_filename(
    *,
    candidate_email: str,
    job_id: int,
    resume_ext: str,
    content: bytes,
) -> str:
    """
    Generate a collision-resistant, traversal-safe filename for storage.
    """
    digest = hashlib.sha256()
    digest.update(candidate_email.lower().strip().encode("utf-8"))
    digest.update(str(job_id).encode("utf-8"))
    # Include a hash of the content to make filename deterministic per resume
    digest.update(hashlib.sha256(content).digest())
    # Safe short suffix for debugging without exposing raw content
    suffix = digest.hexdigest()[:28]
    ext = (resume_ext or "").lower()
    if not ext.startswith("."):
        ext = "." + ext
    return f"{suffix}{ext}"

