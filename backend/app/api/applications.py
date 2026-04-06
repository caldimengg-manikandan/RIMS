from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session, joinedload, selectinload, defer, load_only
import os
import json
import logging
from datetime import datetime, timezone
from app.infrastructure.database import get_db, SessionLocal
from app.domain.models import User, Application, Job, ResumeExtraction, Interview, InterviewAnswer
from app.domain.schemas import (
    ApplicationCreate,
    ApplicationStatusUpdate,
    ApplicationResponse,
    ApplicationDetailResponse,
    ApplicationNotesUpdate,
    HasAppliedResponse,
)
from app.core.auth import get_current_user, get_current_hr
from app.core.ownership import validate_hr_ownership
from app.services.ai_service import parse_resume_with_ai, extract_basic_candidate_info
from app.services.email_service import send_application_received_email, send_rejected_email, send_approved_for_interview_email
import secrets
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import re
import hashlib

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.exc import ObjectDeletedError
from typing import Optional

logger = logging.getLogger(__name__)

# Persisted hint for HR (marker stripped in API responses). Heuristic also sets extraction_degraded.
RIMS_EXTRACTION_DEGRADED_MARKER = "[[rims:extraction_degraded]]"


def _strip_extraction_marker(notes: Optional[str]) -> Optional[str]:
    if not notes:
        return notes
    stripped = notes.replace(RIMS_EXTRACTION_DEGRADED_MARKER, "").strip()
    return stripped if stripped else None


def _append_extraction_degraded_marker(application: Application) -> None:
    current = application.hr_notes or ""
    if RIMS_EXTRACTION_DEGRADED_MARKER in current:
        return
    application.hr_notes = (current.rstrip() + "\n" + RIMS_EXTRACTION_DEGRADED_MARKER).strip()


def _heuristic_extraction_degraded(application: Application) -> bool:
    re = application.resume_extraction
    if not re:
        return False
    summary = re.summary or ""
    if "AI was unable to generate a summary for this resume." in summary:
        return True
    try:
        skills = json.loads(re.extracted_skills or "[]")
    except Exception:
        return False
    if skills == ["General Profile"]:
        return True
    # Avoid triggering a lazy-load of extracted_text (it can be large).
    # If extracted_text isn't loaded in the current query, we can't reliably apply this heuristic.
    try:
        insp = sa_inspect(re)
        if 'extracted_text' not in getattr(insp, "unloaded", set()):
            et = (re.extracted_text or "").strip()
            if et in ("Error extracting text.", "No readable text found."):
                return True
    except Exception:
        # Best-effort: if introspection fails, keep previous behavior as a fallback.
        et = (re.extracted_text or "").strip()
        if et in ("Error extracting text.", "No readable text found."):
            return True
    return False


def build_application_detail_response(application: Application) -> ApplicationDetailResponse:
    detail = ApplicationDetailResponse.model_validate(application, from_attributes=True)
    raw_notes = application.hr_notes or ""
    degraded = RIMS_EXTRACTION_DEGRADED_MARKER in raw_notes or _heuristic_extraction_degraded(application)
    return detail.model_copy(
        update={
            "hr_notes": _strip_extraction_marker(raw_notes),
            "extraction_degraded": degraded,
        }
    )

import asyncio
import time
from pathlib import Path

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

from app.core.config import get_settings
from app.core.idempotency import is_duplicate_request
from app.core.observability import get_request_id, log_json, safe_hash
settings = get_settings()

UPLOAD_DIR = settings.uploads_dir / "resumes"
PRIVATE_UPLOAD_DIR = settings.uploads_dir / "_private_resumes"
PHOTO_DIR = settings.uploads_dir / "photos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PRIVATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PHOTO_DIR.mkdir(parents=True, exist_ok=True)

from app.core.rate_limiter import limiter
from fastapi import Request

router = APIRouter(prefix="/api/applications", tags=["applications"])

@router.get("/ranking/{job_id}")
def get_candidate_ranking(
    job_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get ranked candidates for a specific job (Point 3)"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    validate_hr_ownership(job, current_user, resource_name="job")

    from app.services.candidate_service import CandidateService
    service = CandidateService(db)
    ranked = service.get_ranked_candidates(job_id)
    
    result = []
    for idx, app in enumerate(ranked):
        result.append({
            "rank": idx + 1,
            "id": app.id,
            "candidate_name": app.candidate_name,
            "composite_score": app.composite_score,
            "recommendation": app.recommendation,
            "status": app.status
        })
    return result


@router.post("/apply", response_model=ApplicationResponse)
@limiter.limit("5/minute")
async def apply_for_job(
    request: Request,
    job_id: int = Form(...),
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    candidate_phone: str = Form(None),
    resume_file: UploadFile = File(...),
    photo_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Apply for a job with resume (Public endpoint)"""
    # Strict input validation
    # Name: at least two words, alphabetic only (plus spaces)
    if not candidate_name or len(candidate_name.split()) < 2 or not all(part.isalpha() for part in candidate_name.split()):
        raise HTTPException(
            status_code=400,
            detail="Valid full name required (at least two words, alphabetic characters only)."
        )

    request_id = None
    ip_address = None
    try:
        request_id = get_request_id(request)
        if request and request.client:
            ip_address = request.client.host
    except Exception:
        request_id = None
        ip_address = None

    # Email: centralized strict validation + structured logging (non-breaking)
    try:
        from app.core.email_utils import validate_email_strict_enterprise

        candidate_email = validate_email_strict_enterprise(
            candidate_email,
            ip=ip_address,
            request_id=request_id,
            logger=logger,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Non-blocking flag for obviously fake/test domains (H-domain hygiene)
    suspicious_email_domain = None
    try:
        # Minimal, explicit list to avoid over-blocking; can be extended safely later.
        DISPOSABLE_DOMAINS = {
            "fengnu.com",
            "mailinator.com",
            "guerrillamail.com",
            "10minutemail.com",
            "tempmail.com",
        }
        _, domain_part = candidate_email.rsplit("@", 1)
        domain_part = domain_part.lower().strip()
        if domain_part in DISPOSABLE_DOMAINS:
            suspicious_email_domain = domain_part
    except Exception:
        suspicious_email_domain = None

    # Phone: Numeric only, 10-15 digits (H004) + raw audit storage (non-breaking)
    from app.core.phone_utils import compute_phone_hash, normalize_phone_digits

    candidate_phone_raw = candidate_phone if candidate_phone else None
    normalized_digits = None
    phone_error_reason = None
    if candidate_phone:
        normalized_digits, phone_error_reason = normalize_phone_digits(candidate_phone)

    if normalized_digits is None and phone_error_reason is not None:
        try:
            from app.core.observability import log_json

            log_json(
                logger,
                "phone_validation_rejected",
                request_id=request_id,
                endpoint="/api/applications/apply",
                user_id=None,
                status=400,
                level="warning",
                extra={"reason": phone_error_reason},
            )
        except Exception:
            pass
        if phone_error_reason in ("letters_present", "invalid_length"):
            raise HTTPException(status_code=400, detail="Phone number must be 10–15 digits")
        if phone_error_reason == "invalid_characters":
            raise HTTPException(status_code=400, detail="Phone number must contain only digits (and separators)")
        raise HTTPException(status_code=400, detail="Phone number must be 10–15 digits")

    candidate_phone = normalized_digits if normalized_digits else None
    candidate_phone_hash = compute_phone_hash(candidate_phone) if candidate_phone else None

    # Check if job exists and is open
    job = db.query(Job).filter(Job.id == job_id, Job.status == "open").first()
    if not job:
        try:
            from app.core.observability import log_json
            log_json(
                logger,
                "validation_failed",
                request_id=request_id,
                endpoint="/api/applications/apply",
                status=404,
                level="warning",
                extra={"module": "applications", "field": "job_id", "reason": "not_found_or_closed", "input_preview": str(job_id)},
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not open"
        )

    request_id_header = request.headers.get("X-Request-ID")
    if settings.enable_request_id_idempotency and is_duplicate_request(
        request_id=request_id_header,
        scope="applications.apply",
        key=f"{candidate_email.lower().strip()}:{job_id}",
        ttl_seconds=60,
    ):
        existing_idem = (
            db.query(Application)
            .filter(
                Application.job_id == job_id,
                Application.candidate_email == candidate_email,
            )
            .first()
        )
        if existing_idem:
            log_json(
                logger,
                "apply_idempotent_replay",
                request_id=request_id,
                endpoint="/api/applications/apply",
                level="info",
                extra={
                    "application_id": existing_idem.id,
                    "job_id": job_id,
                    "email_hash": safe_hash(candidate_email),
                },
            )
            return existing_idem
        raise HTTPException(
            status_code=409,
            detail="Duplicate application request detected. Please wait and retry.",
        )

    # A002: Prevent duplicate candidate entries by email OR phone per job.
    # IMPORTANT: This guard uses ONLY the manually-typed email and phone hash
    # from this request. AI-extracted emails from resumes are *never* used here.
    from sqlalchemy import or_
    existing_app = db.query(Application).filter(
        Application.job_id == job_id,
        or_(
            Application.candidate_email == candidate_email,
            (Application.candidate_phone_hash == candidate_phone_hash) if candidate_phone_hash else False,
        ),
    ).first()

    if existing_app:
        # Only treat this as a hard duplicate when the manually-typed email matches.
        if existing_app.candidate_email == candidate_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied for this job",
            )
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
    ALLOWED_RESUME_MIMES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    from app.core.resume_upload_utils import (
        generate_hashed_resume_filename,
        get_resume_extension,
        validate_resume_signature,
    )

    resume_ext = get_resume_extension(resume_file.filename)
    if resume_ext not in ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resume file type. Only .pdf and .docx are allowed.",
        )
    content = await resume_file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume file is empty.")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB.",
        )
    # Basic signature validation (keeps previous behavior/messages).
    ok, reason = validate_resume_signature(resume_ext, content)
    if not ok:
        if reason == "invalid_pdf_signature":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF content.")
        if reason == "invalid_docx_signature":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid DOCX content.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resume content.")

    # Optional MIME sniff (defense in depth; non-fatal if it disagrees with client header).
    try:
        # python-magic is optional; if not installed we skip.
        import magic  # type: ignore

        mime = magic.from_buffer(content, mime=True)
        if mime and mime not in ALLOWED_RESUME_MIMES:
            logger.warning(
                "Resume MIME mismatch (non-fatal)",
                extra={
                    "resume_mime": mime,
                    "resume_ext": resume_ext,
                },
            )
    except Exception:
        pass

    # Save resume file using hashed filename to avoid collisions/path traversal risks.
    filename = generate_hashed_resume_filename(
        candidate_email=candidate_email,
        job_id=job_id,
        resume_ext=resume_ext,
        content=content,
    )
    abs_file_path = os.path.join(PRIVATE_UPLOAD_DIR, filename).replace("\\", "/")
    # Relative path for storage (used by the secure download endpoint)
    rel_file_path = f"uploads/_private_resumes/{filename}"

    with open(abs_file_path, "wb") as f:
        f.write(content)

    # Non-blocking virus scan hook stub (best-effort).
    def _virus_scan_stub(path: str) -> None:
        try:
            # Replace with a real scanner later; kept as a no-op for now.
            logger.info("Virus scan stub executed", extra={"path": path})
        except Exception:
            pass

    background_tasks.add_task(_virus_scan_stub, abs_file_path)

    try:
        from app.core.observability import log_json, safe_hash

        log_json(
            logger,
            "resume_upload_success",
            request_id=request_id,
            user_id=None,
            endpoint="/api/applications/apply",
            status=200,
            level="info",
            extra={"resume_ext": resume_ext, "file_hash": safe_hash(filename), "email_hash": safe_hash(candidate_email)},
        )
    except Exception:
        pass
    
    safe_email = candidate_email.replace('@', '_').replace('.', '_')

    # Save photo file (basic safety only; resume is strictly enforced per requirements)
    rel_photo_path = None
    abs_photo_path = None
    if not photo_file:
        raise HTTPException(status_code=400, detail="Candidate photo is required.")

    photo_content = await photo_file.read()
    if not photo_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate photo is empty.")
    if len(photo_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo too large. Maximum size is 5MB.",
        )

    photo_ext = (Path(photo_file.filename or "").suffix.lower() or ".jpg").lstrip(".")
    photo_filename = f"photo_{safe_email}_{job_id}_{datetime.now(timezone.utc).timestamp()}.{photo_ext}"

    # Absolute path for saving
    abs_photo_path = os.path.join(PHOTO_DIR, photo_filename).replace("\\", "/")
    # Relative path for DB
    rel_photo_path = f"uploads/photos/{photo_filename}"

    with open(abs_photo_path, "wb") as f:
        f.write(photo_content)
    
    # Create application
    warning_notes = None
    if suspicious_email_domain:
        warning_notes = (
            f"Warning: Possibly fake/test email domain detected ({suspicious_email_domain})."
        )

    new_application = Application(
        job_id=job_id,
        hr_id=job.hr_id,  # Set denormalized field for performance
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        candidate_phone=candidate_phone,
        candidate_phone_raw=candidate_phone_raw,
        candidate_phone_hash=candidate_phone_hash,
        resume_file_path=rel_file_path,
        resume_file_name=resume_file.filename,
        candidate_photo_path=rel_photo_path,
        status="applied",
        hr_notes=warning_notes,
    )

    def _retry_delete_file(path: str, attempts: int = 3) -> None:
        """Best-effort delete with retries to avoid intermittent filesystem issues."""
        if not path:
            return
        for attempt in range(1, attempts + 1):
            try:
                if os.path.exists(path):
                    os.remove(path)
                return
            except Exception as e:
                logger.warning(
                    "File cleanup retry failed",
                    extra={"path": path, "attempt": attempt, "error": str(e)},
                )
                # Backoff between retries (small, to keep endpoint responsive)
                time.sleep(0.05 * attempt)
    
    try:
        db.add(new_application)
        db.flush()  # Get ID without committing

        # ── Send HR Notification ──
        from app.domain.models import Notification, AuditLog

        hr_notification = Notification(
            user_id=job.hr_id,
            notification_type="new_application",
            title=f"New Application: {candidate_name}",
            message=f"{candidate_name} has applied for {job.title}.",
            related_application_id=new_application.id,
        )
        db.add(hr_notification)

        # Best-effort audit log for obviously fake/test email domains.
        if suspicious_email_domain:
            try:
                audit = AuditLog(
                    user_id=None,
                    action="POSSIBLY_FAKE_EMAIL_DOMAIN",
                    resource_type="Application",
                    resource_id=new_application.id,
                    details=(
                        f"Application #{new_application.id} uses disposable-like domain: {suspicious_email_domain}"
                    ),
                    ip_address=ip_address,
                )
                db.add(audit)
            except Exception:
                # Logging issues should never block application creation.
                logger.warning(
                    "Failed to create audit log for suspicious email domain",
                    extra={"domain": suspicious_email_domain},
                )

        db.commit()
        db.refresh(new_application)
    except IntegrityError:
        db.rollback()
        # Best-effort cleanup for already-written files.
        _retry_delete_file(abs_file_path)
        _retry_delete_file(abs_photo_path)
        # Handle duplicate race conditions gracefully
        from sqlalchemy import or_
        existing = db.query(Application).filter(
            Application.job_id == job_id,
            or_(
                Application.candidate_email == candidate_email,
                (Application.candidate_phone_hash == candidate_phone_hash) if candidate_phone_hash else False
            )
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already applied for this job.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application already exists.")
    except Exception as e:
        db.rollback()
        # Best-effort cleanup for already-written files.
        _retry_delete_file(abs_file_path)
        _retry_delete_file(abs_photo_path)
        try:
            import sentry_sdk  # type: ignore

            sentry_sdk.capture_exception(e)
        except Exception:
            pass
        logger.error(f"Error saving application/notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to save application securely")
    
    # 1. Notify candidate immediately of receipt
    background_tasks.add_task(send_application_received_email, candidate_email, job.title)

    # 2. Move all heavy processing to background task to prevent timeouts
    background_tasks.add_task(
        process_application_background, 
        new_application.id, 
        job_id, 
        abs_file_path, 
        candidate_email, 
        candidate_name
    )
    
    return new_application

async def process_application_background(application_id: int, job_id: int, abs_file_path: str, candidate_email: str, candidate_name: str):
    """Heavy AI processing and notification workflow in background"""
    db = SessionLocal()
    try:
        from app.services.candidate_service import CandidateService
        cand_service = CandidateService(db)
        
        # Reload objects in this session
        # Step 1: lock only (without joins)
        # Note: Application.resume_extraction is configured as lazy='joined', so ORM-level
        # .with_for_update() may turn into a LEFT OUTER JOIN, which Postgres rejects.
        from sqlalchemy import text
        db.execute(text("SELECT 1 FROM applications WHERE id = :id FOR UPDATE"), {"id": application_id})
        
        # Step 2: fetch with joins, no lock
        application = db.query(Application).options(
            joinedload(Application.resume_extraction)
        ).filter(Application.id == application_id).first()
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if not application or not job:
            db.close()
            return

        application.resume_status = "parsing"
        db.commit()
        db.refresh(application)
        try:
            log_json(
                logger,
                "resume_parsing_started",
                level="info",
                extra={"application_id": application_id, "job_id": job_id},
            )
        except Exception:
            pass

        # 1. Initial State
        cand_service.advance_stage(application_id, "Application Submitted", "pass")
        cand_service.create_audit_log(None, "APPLICATION_SUBMITTED", "Application", application_id, {"email": candidate_email})
        
        # 2. Screening Stage
        cand_service.advance_stage(application_id, "Resume Screening", "pending")
        
        # Parse resume text based on file type
        resume_text = ""
        try:
            file_ext = abs_file_path.lower().split('.')[-1]
            if file_ext == 'pdf':
                from pypdf import PdfReader
                if not os.path.exists(abs_file_path):
                    logger.error(f"[ERROR] Resume file not found at: {abs_file_path}")
                    raise FileNotFoundError(f"Resume file not found: {abs_file_path}")
                reader = PdfReader(abs_file_path)
                for page in reader.pages:
                    resume_text += page.extract_text() + "\n"
            elif file_ext in ['docx', 'doc']:
                import docx
                doc = docx.Document(abs_file_path)
                for para in doc.paragraphs:
                    resume_text += para.text + "\n"
            else:
                with open(abs_file_path, "rb") as f:
                    resume_text = f.read().decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Background Text Extraction Error: {e}")
            cand_service.create_audit_log(None, "RESUME_TEXT_EXTRACTION_FAILED", "Application", application_id, {"error": str(e)})
            resume_text = "Error extracting text."
        
        if not resume_text.strip():
            resume_text = "No readable text found."

        # AI Parsing
        extraction_data = await parse_resume_with_ai(resume_text, job_id, job.description, job.experience_level)
        extraction_degraded_flag = extraction_data.pop("extraction_degraded", False)

        # Store extraction (Upsert pattern for robustness)
        resume_extraction = db.query(ResumeExtraction).filter(ResumeExtraction.application_id == application_id).first()
        if not resume_extraction:
            resume_extraction = ResumeExtraction(application_id=application_id)
            db.add(resume_extraction)
            
        resume_extraction.extracted_text = resume_text
        resume_extraction.summary = extraction_data.get("summary", "")
        resume_extraction.extracted_skills = json.dumps(extraction_data.get("skills") or [])
        resume_extraction.years_of_experience = extraction_data.get("experience")
        resume_extraction.education = json.dumps(extraction_data.get("education") or [])
        resume_extraction.previous_roles = json.dumps(extraction_data.get("roles") or [])
        resume_extraction.experience_level = extraction_data.get("experience_level")
        resume_extraction.resume_score = extraction_data.get("score", 0)
        resume_extraction.skill_match_percentage = extraction_data.get("match_percentage", 0)
        
        if extraction_data.get("candidate_name"):
            resume_extraction.candidate_name = extraction_data.get("candidate_name")
        if extraction_data.get("email"):
            resume_extraction.email = extraction_data.get("email")
        if extraction_data.get("phone_number"):
            resume_extraction.phone_number = extraction_data.get("phone_number")
        
        # Update Application summary fields
        application.resume_score = extraction_data.get("score", 0)
        
        # ── HYBRID IDENTITY EXTRACTION: AI + regex fallback ──
        from app.services.ai_service import extract_email_regex, extract_phone_regex, extract_name_heuristic
        
        extracted_name = extraction_data.get("candidate_name") or extract_name_heuristic(resume_text)
        extracted_email = extraction_data.get("email") or extract_email_regex(resume_text)
        extracted_phone = extraction_data.get("phone_number") or extract_phone_regex(resume_text)
        
        logger.info(f"[IDENTITY SYNC] App #{application_id} | EXTRACTED: name={extracted_name}, email={extracted_email}, phone={extracted_phone}")
        
        is_duplicate = False
        duplicate_app_id = None
        
        # 1. Duplicate Detection via Extracted Email
        if extracted_email:
            norm_email = extracted_email.lower().strip()
            existing_match = db.query(Application).filter(
                Application.job_id == job_id,
                Application.candidate_email == norm_email,
                Application.id != application_id
            ).first()
            
            if existing_match:
                is_duplicate = True
                duplicate_app_id = existing_match.id
                logger.info(f"[IDENTITY SYNC] App #{application_id} Conflict: '{norm_email}' already applied to job {job_id}")
                # Internal-only signal: mark HR notes and pipeline stage as possible duplicate.
                application.hr_notes = (application.hr_notes or "") + f"\nNotice: AI detected this as a duplicate of App ID: {duplicate_app_id} (matched on email in resume)."
            else:
                # Safe to update email if it was missing or obviously wrong (placeholder)
                if not application.candidate_email or "@batch.local" in application.candidate_email:
                    application.candidate_email = extracted_email
                    logger.info(f"[IDENTITY SYNC] App #{application_id} | Email updated from resume")

        # 2. Name & Phone Sync (Conservative)
        # We only overwrite if the current value is "weak" (one word name or missing phone)
        if extracted_name and (not application.candidate_name or len(application.candidate_name.split()) < 2):
            application.candidate_name = extracted_name
            logger.info(f"[IDENTITY SYNC] App #{application_id} | Name updated from resume")
            
        if extracted_phone and not application.candidate_phone:
            application.candidate_phone = extracted_phone
            logger.info(f"[IDENTITY SYNC] App #{application_id} | Phone updated from resume")

        if extraction_degraded_flag:
            _append_extraction_degraded_marker(application)

        application.resume_status = "parsed"
        db.commit()
        db.refresh(application)
        try:
            log_json(
                logger,
                "resume_parsing_completed",
                level="info",
                extra={"application_id": application_id, "resume_status": "parsed"},
            )
        except Exception:
            pass

        # ── Pipeline Advancement ──
        # If duplicate, we mark stage as 'fail' so it's not advanced, but we STILL provide the real score.
        # This is *internal-only* and never surfaces as a 409 or candidate-facing error.
        # If not duplicate, we mark as 'pass' to await HR decision.
        stage_status = "fail" if is_duplicate else "pass"
        stage_note = (
            f"Possible duplicate of App #{duplicate_app_id}"
            if is_duplicate
            else "AI analysis complete — awaiting HR decision"
        )
        
        cand_service.advance_stage(
            application_id, 
            "Resume Screening", 
            stage_status, 
            extraction_data.get("score", 0) * 10, 
            stage_note
        )
        cand_service.create_audit_log(None, "RESUME_SCREENING_COMPLETED", "Application", application_id, 
                                      {"score": extraction_data.get("score", 0), "match": extraction_data.get("match_percentage", 0)})
        
        db.commit()
    except Exception as e:
        logger.error(
            f"CRITICAL Background Error processing application {application_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        # Log the critical error
        try:
            cand_service = CandidateService(db) # Re-initialize if needed, or pass db
            cand_service.create_audit_log(None, "BACKGROUND_PROCESSING_FAILED", "Application", application_id, {"error": str(e)})
            # Optionally update application status to indicate processing failed
            application = db.query(Application).filter(Application.id == application_id).first()
            if application:
                application.status = "applied"  # Keep in 'applied' — HR can retry or proceed manually
                application.resume_status = "failed"
                # Never write raw exception details (may include internal SQL / query text) into HR-visible notes.
                application.hr_notes = (
                    "AI analysis failed. Please click "
                    "Retry Analysis to reprocess."
                )
                _append_extraction_degraded_marker(application)
                db.commit()
                try:
                    log_json(
                        logger,
                        "resume_parsing_failed",
                        level="error",
                        extra={"application_id": application_id, "resume_status": "failed"},
                    )
                except Exception:
                    pass
        except Exception as log_e:
            logger.error(f"Failed to log critical error for application {application_id}: {log_e}")
    finally:
        db.close()
    
    # The return value of a background task is not used by FastAPI.
    # The original snippet returned new_application, but it's not necessary here.
    # Keeping it for consistency with the provided snippet, but it has no effect.
    return application


@router.get("/has-applied", response_model=HasAppliedResponse)
@limiter.limit("20/minute")
def has_applied_for_job(
    request: Request,
    job_id: int,
    candidate_email: str,
    db: Session = Depends(get_db),
):
    """Return whether a (job_id, candidate_email) application already exists.

    This is a public helper used by the Apply UI to disable the submit button
    before triggering the POST /api/applications/apply 409 path.
    """
    try:
        from app.core.email_utils import validate_email_strict_enterprise

        candidate_email = validate_email_strict_enterprise(
            candidate_email,
            ip=None,
            request_id=None,
            logger=logger,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    existing = (
        db.query(Application.id)
        .filter(
            Application.job_id == job_id,
            Application.candidate_email == candidate_email,
        )
        .first()
    )
    return HasAppliedResponse(hasApplied=existing is not None)


@router.get("/pending-count")
def get_pending_applications_count(
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """Sidebar / badges: count applications not in a terminal state, scoped to HR's jobs."""
    q = db.query(Application).filter(~Application.status.in_(("hired", "rejected")))
    if current_user.role != "super_admin":
        q = q.join(Job, Application.job_id == Job.id).filter(Job.hr_id == current_user.id)
    return {"count": q.count()}


@router.get("", response_model=list[ApplicationDetailResponse])
def get_hr_applications(
    job_id: int = None,
    from_date: str = None,
    to_date: str = None,
    status: str = None,
    time_range: str = None,
    search: str = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get all applications for HR's jobs (HR only)"""
    # Performance Optimization:
    # - Avoid loading huge `resume_extraction.extracted_text` (not needed by HR list UI).
    # - Only join `jobs` when we filter on job columns.
    query = db.query(Application).options(
        joinedload(Application.job).load_only(Job.id, Job.title, Job.hr_id, Job.status),
        joinedload(Application.resume_extraction).load_only(
            ResumeExtraction.id, ResumeExtraction.resume_score,
            ResumeExtraction.skill_match_percentage, ResumeExtraction.experience_level,
            ResumeExtraction.summary, ResumeExtraction.extracted_skills,
        ),
        joinedload(Application.interview).load_only(Interview.id, Interview.status, Interview.overall_score),
        selectinload(Application.pipeline_stages),
    )

    needs_job_join = bool(search and str(search).strip()) or current_user.role != "super_admin"
    if needs_job_join:
        query = query.outerjoin(Job)
    
    # Filter by job if requested
    if job_id:
        query = query.filter(Application.job_id == job_id)

    # Server-side search across candidate, job, and application id (paginated with skip/limit)
    if search and str(search).strip():
        from sqlalchemy import String, cast, or_
        qraw = str(search).strip()[:200]
        term = f"%{qraw}%"
        query = query.filter(
            or_(
                Application.candidate_name.ilike(term),
                Application.candidate_email.ilike(term),
                Job.title.ilike(term),
                Job.job_id.ilike(term),
                cast(Application.id, String).ilike(term),
            )
        )

    # Status filter (HR UI "Applied" includes legacy/submitted)
    if status:
        if status == "applied":
            query = query.filter(Application.status.in_(("applied", "submitted")))
        else:
            query = query.filter(Application.status == status)

    # Date range filter (A004/A005/A009)
    from sqlalchemy import func
    today_utc = datetime.now(timezone.utc).date()
    min_year = 1900
    max_year = today_utc.year

    start_date = None
    end_date = None

    if from_date:
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(
                "Invalid from_date format in HR applications filter",
                extra={"from_date": from_date},
            )
            raise HTTPException(status_code=400, detail="Invalid from_date format. Use YYYY-MM-DD.")

        if start_date.year < min_year or start_date.year > max_year:
            logger.warning(
                "from_date out of allowed range in HR applications filter",
                extra={"from_date": from_date, "min_year": min_year, "max_year": max_year},
            )
            raise HTTPException(status_code=400, detail="from_date out of allowed range.")
        if start_date > today_utc:
            logger.warning(
                "from_date is in the future in HR applications filter",
                extra={"from_date": from_date, "today_utc": str(today_utc)},
            )
            raise HTTPException(status_code=400, detail="from_date cannot be in the future.")

    if to_date:
        try:
            end_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(
                "Invalid to_date format in HR applications filter",
                extra={"to_date": to_date},
            )
            raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD.")

        if end_date.year < min_year or end_date.year > max_year:
            logger.warning(
                "to_date out of allowed range in HR applications filter",
                extra={"to_date": to_date, "min_year": min_year, "max_year": max_year},
            )
            raise HTTPException(status_code=400, detail="to_date out of allowed range.")
        if end_date > today_utc:
            logger.warning(
                "to_date is in the future in HR applications filter",
                extra={"to_date": to_date, "today_utc": str(today_utc)},
            )
            raise HTTPException(status_code=400, detail="to_date cannot be in the future.")

    if start_date and end_date and start_date > end_date:
        logger.warning(
            "from_date after to_date in HR applications filter",
            extra={"from_date": from_date, "to_date": to_date},
        )
        raise HTTPException(status_code=400, detail="from_date cannot be after to_date.")

    # UTC-safe date comparison: date(timezone('UTC', applied_at)) >= start/end
    if start_date:
        query = query.filter(func.date(func.timezone("UTC", Application.applied_at)) >= start_date)
    if end_date:
        query = query.filter(func.date(func.timezone("UTC", Application.applied_at)) <= end_date)

    # Time-of-day filter
    if time_range and time_range in ("morning", "afternoon", "evening", "night"):
        from sqlalchemy import text, extract
        hour_expr = extract('hour', text("(\"applications\".\"applied_at\" AT TIME ZONE 'UTC') AT TIME ZONE 'Asia/Kolkata'"))
        if time_range == "morning":
            query = query.filter(hour_expr.between(6, 11))
        elif time_range == "afternoon":
            query = query.filter(hour_expr.between(12, 17))
        elif time_range == "evening":
            query = query.filter(hour_expr.between(18, 23))
        elif time_range == "night":
            query = query.filter(hour_expr.between(0, 5))

    # Security: Hybrid HR Filter for guaranteed visibility
    if current_user.role != "super_admin":
        from sqlalchemy import or_
        query = query.filter(or_(Application.hr_id == current_user.id, Job.hr_id == current_user.id))
        
    # Pagination safety (A007/A008): cap limit to keep queries predictable.
    safe_skip = max(0, int(skip or 0))
    # Default to 20; hard cap at 50 to prevent huge payloads.
    safe_limit = max(1, min(int(limit or 20), 50))

    t0 = time.perf_counter()
    applications = (
        query.order_by(Application.applied_at.desc())
        .offset(safe_skip)
        .limit(safe_limit)
        .all()
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if elapsed_ms > 200:
        logger.warning(
            "HR applications query slow",
            extra={"elapsed_ms": elapsed_ms, "user_id": current_user.id, "limit": safe_limit},
        )
    else:
        logger.info(f"Retrieved {len(applications)} applications for user {current_user.id} (Optimized Query)")

    # Before returning, inspect and nullify any detached/deleted relationships
    for app in applications:
        if not app.resume_extraction: continue
        try:
            insp = sa_inspect(app.resume_extraction)
            if insp.detached or insp.deleted:
                app.resume_extraction = None
        except Exception:
            app.resume_extraction = None

    # Path sanitization for frontend consumption
    for app in applications:
        if app.candidate_photo_path and "uploads" in app.candidate_photo_path:
            idx = app.candidate_photo_path.find("uploads")
            app.candidate_photo_path = app.candidate_photo_path[idx:].replace("\\", "/")
        if app.resume_file_path and "uploads" in app.resume_file_path:
            idx = app.resume_file_path.find("uploads")
            app.resume_file_path = app.resume_file_path[idx:].replace("\\", "/")

    return [build_application_detail_response(app) for app in applications]

@router.get("/{application_id}/resume/download")
def download_resume(
    application_id: int,
    request: Request,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Securely download a candidate's resume (HR only)"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application or not application.resume_file_path:
        raise HTTPException(status_code=404, detail="Resume file not found")
    validate_hr_ownership(application, current_user, resource_name="application")

    # A006: Robust file path resolution using strictly sanitized filename
    stored_path = (application.resume_file_path or "").replace("\\", "/")
    filename = os.path.basename(stored_path)

    # Candidate 1: expected new format: <uploads>/resumes/<filename>
    candidate_1 = settings.uploads_dir / "resumes" / filename

    # Candidate 2: stored path includes "uploads/<subpath>"
    # e.g. uploads/resumes/<filename> -> resumes/<filename> under uploads_dir
    candidate_2 = None
    if "uploads/" in stored_path:
        rel = stored_path.split("uploads/", 1)[1]
        candidate_2 = settings.uploads_dir / rel

    # Candidate 3: legacy fallback: <uploads>/<filename>
    candidate_3 = settings.uploads_dir / filename

    file_path = None
    for c in [candidate_1, candidate_2, candidate_3]:
        if c and c.exists():
            file_path = c
            break

    if not file_path:
        try:
            from app.core.observability import get_request_id, log_json

            log_json(
                logger,
                "resume_download_not_found",
                request_id=get_request_id(request),
                endpoint="/api/applications/{application_id}/resume/download",
                user_id=current_user.id,
                status=404,
                level="warning",
                extra={
                    "application_id": application_id,
                    "stored_path": stored_path,
                    "resolved_filename": filename,
                },
            )
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="Resume file not found on server")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        filename=application.resume_file_name or filename,
        media_type='application/octet-stream'
    )

@router.get("/{application_id}", response_model=ApplicationDetailResponse)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Get application details (HR only)"""
    application = db.query(Application).options(
        joinedload(Application.job),
        joinedload(Application.resume_extraction),
        joinedload(Application.interview),
        selectinload(Application.pipeline_stages)
    ).filter(Application.id == application_id).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    validate_hr_ownership(application, current_user, resource_name="application")
    
    # Sanitize paths
    if application.candidate_photo_path and ":" in application.candidate_photo_path:
        idx = application.candidate_photo_path.find("uploads")
        if idx != -1:
            application.candidate_photo_path = application.candidate_photo_path[idx:].replace("\\", "/")
    if application.resume_file_path and ":" in application.resume_file_path:
        idx = application.resume_file_path.find("uploads")
        if idx != -1:
            application.resume_file_path = application.resume_file_path[idx:].replace("\\", "/")

    return build_application_detail_response(application)

async def retry_application_background(application_id: int, job_id: int, abs_file_path: str):
    """Safely retry AI resume extraction without altering pipeline stages or triggering emails."""
    db = SessionLocal()
    try:
        from app.services.candidate_service import CandidateService
        cand_service = CandidateService(db)
        
        # Reload objects in this session
        # Step 1: lock only (without joins)
        # Note: Application.resume_extraction is configured as lazy='joined', so ORM-level
        # .with_for_update() may turn into a LEFT OUTER JOIN, which Postgres rejects.
        from sqlalchemy import text
        db.execute(text("SELECT 1 FROM applications WHERE id = :id FOR UPDATE"), {"id": application_id})
        
        # Step 2: fetch with joins, no lock
        application = db.query(Application).options(
            joinedload(Application.resume_extraction)
        ).filter(Application.id == application_id).first()
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if not application or not job:
            db.close()
            return
            
        logger.info(f"Retrying AI extraction for application {application_id}...")
        
        # Parse resume text based on file type
        resume_text = ""
        try:
            file_ext = abs_file_path.lower().split('.')[-1]
            if file_ext == 'pdf':
                from pypdf import PdfReader
                reader = PdfReader(abs_file_path)
                for page in reader.pages:
                    resume_text += page.extract_text() + "\n"
            elif file_ext in ['docx', 'doc']:
                import docx
                doc = docx.Document(abs_file_path)
                for para in doc.paragraphs:
                    resume_text += para.text + "\n"
            else:
                with open(abs_file_path, "rb") as f:
                    resume_text = f.read().decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Retry Text Extraction Error: {e}", exc_info=True)
            cand_service.create_audit_log(None, "RETRY_TEXT_EXTRACTION_FAILED", "Application", application_id, {"error": str(e)})
            resume_text = "Error extracting text."
        
        if not resume_text.strip():
            resume_text = "No readable text found."

        # AI Parsing
        extraction_data = await parse_resume_with_ai(resume_text, job_id, job.description, job.experience_level)
        extraction_degraded_flag = extraction_data.pop("extraction_degraded", False)

        # Look for existing extraction or create new
        resume_extraction = db.query(ResumeExtraction).filter(ResumeExtraction.application_id == application_id).first()
        if not resume_extraction:
            resume_extraction = ResumeExtraction(application_id=application_id)
            db.add(resume_extraction)
            
        resume_extraction.extracted_text = resume_text
        resume_extraction.summary = extraction_data.get("summary", "")
        resume_extraction.extracted_skills = json.dumps(extraction_data.get("skills") or [])
        resume_extraction.years_of_experience = extraction_data.get("experience")
        resume_extraction.education = json.dumps(extraction_data.get("education") or [])
        resume_extraction.previous_roles = json.dumps(extraction_data.get("roles") or [])
        resume_extraction.experience_level = extraction_data.get("experience_level")
        resume_extraction.resume_score = extraction_data.get("score", 0)
        resume_extraction.skill_match_percentage = extraction_data.get("match_percentage", 0)
        
        if extraction_data.get("candidate_name"):
            resume_extraction.candidate_name = extraction_data.get("candidate_name")
        if extraction_data.get("email"):
            resume_extraction.email = extraction_data.get("email")
        if extraction_data.get("phone_number"):
            resume_extraction.phone_number = extraction_data.get("phone_number")
        
        application.resume_score = extraction_data.get("score", 0)
        
        if "@batch.local" in application.candidate_email:
            if extraction_data.get("candidate_name"):
                application.candidate_name = extraction_data.get("candidate_name")
            if extraction_data.get("email"):
                application.candidate_email = extraction_data.get("email")
            if extraction_data.get("phone_number"):
                application.candidate_phone = extraction_data.get("phone_number")

        if extraction_degraded_flag:
            _append_extraction_degraded_marker(application)

        application.resume_status = "parsed"
        db.commit()
        cand_service.create_audit_log(None, "AI_ANALYSIS_RETRY_SUCCESS", "Application", application_id, {"score": extraction_data.get("score")})
        logger.info(f"Retry successful for application {application_id}")
        try:
            log_json(
                logger,
                "resume_retry_background_completed",
                level="info",
                extra={"application_id": application_id, "resume_status": "parsed"},
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(
            f"Retry Background Error processing application {application_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        try:
            cand_service = CandidateService(db)
            cand_service.create_audit_log(None, "AI_ANALYSIS_RETRY_FAILED", "Application", application_id, {"error": str(e)})
            failed_app = db.query(Application).filter(Application.id == application_id).first()
            if failed_app:
                failed_app.resume_status = "failed"
                # Never write raw exception details (may include internal SQL / query text) into HR-visible notes.
                failed_app.hr_notes = (
                    "AI analysis failed. Please click "
                    "Retry Analysis to reprocess."
                )
                db.commit()
            try:
                log_json(
                    logger,
                    "resume_retry_background_failed",
                    level="error",
                    extra={"application_id": application_id, "resume_status": "failed"},
                )
            except Exception:
                pass
        except Exception:
            pass
    finally:
        db.close()

@router.post("/{application_id}/retry-analysis")
async def retry_resume_analysis(
    application_id: int, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Manually trigger AI resume analysis if it failed"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    validate_hr_ownership(application, current_user, resource_name="application")
        
    abs_file_path = ""
    if application.resume_file_path:
        # Resolve the actual file path using application settings
        # In the DB, it's typically 'uploads/resumes/filename.pdf'
        # settings.uploads_dir is 'D:\CALDIM\ars\RIMS\backend\uploads'
        clean_path = application.resume_file_path
        if clean_path.startswith("uploads/"):
             clean_path = clean_path[8:]
        elif clean_path.startswith("uploads\\"):
             clean_path = clean_path[8:]
        
        abs_file_path = str(settings.uploads_dir / clean_path)
        
    if not abs_file_path or not os.path.exists(abs_file_path):
         logger.error(f"Error locating file path: DB path='{application.resume_file_path}', Tried path='{abs_file_path}'")
         raise HTTPException(status_code=400, detail="Resume file not found on server")

    application.resume_status = "parsing"
    application.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(application)
    try:
        log_json(
            logger,
            "resume_retry_api_accepted",
            level="info",
            extra={
                "application_id": application_id,
                "hr_user_id": current_user.id,
                "resume_status": "parsing",
            },
        )
    except Exception:
        pass

    background_tasks.add_task(
        retry_application_background, 
        application.id, 
        application.job_id, 
        abs_file_path
    )
    
    return {
        "status": "success",
        "message": "Analysis restarted in background safely",
        "application_id": application_id,
        "resume_status": "parsing",
    }

@router.post("/{application_id}/resend-interview-invitation")
async def resend_interview_invitation(
    application_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """
    Re-send the interview invitation email.

    This is useful when the original "approve_for_interview" succeeded but the email
    provider (e.g. Gmail quota) failed. We re-issue the interview access key only when
    the interview is missing or still 'not_started'.
    """
    application = db.query(Application).options(
        joinedload(Application.job),
        joinedload(Application.interview),
    ).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    validate_hr_ownership(application, current_user, resource_name="application")

    # If an interview exists and is already in progress/completed, don't re-issue the key.
    if application.interview and getattr(application.interview, "status", None) != "not_started":
        raise HTTPException(
            status_code=400,
            detail="Interview access key cannot be reissued unless interview is 'not_started'",
        )

    raw_access_key = _ensure_interview_record(application, db)
    candidate_email = application.candidate_email
    job_title = application.job.title if application.job else "your applied position"

    background_tasks.add_task(
        send_approved_for_interview_email,
        candidate_email,
        job_title,
        raw_access_key,
    )

    try:
        log_json(
            logger,
            "resume_invite_email_resend_scheduled",
            level="info",
            extra={"application_id": application_id, "to": candidate_email},
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": "Interview invitation email scheduled in background",
        "application_id": application_id,
    }

@router.put("/{application_id}/status")
async def update_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """
    Execute a state transition on an application via the finite state machine.
    
    The frontend sends an 'action' (e.g. 'approve_for_interview', 'reject', 
    'call_for_interview', 'review_later', 'hire').  The FSM validates the 
    transition, updates the status atomically, logs the change, and returns 
    the result including which email to send.
    """
    from app.services.state_machine import (
        CandidateStateMachine, TransitionAction,
        InvalidTransitionError, DuplicateTransitionError,
    )

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    validate_hr_ownership(application, current_user, resource_name="application")

    # Parse the action
    try:
        action = TransitionAction(status_update.action)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: '{status_update.action}'. "
                   f"Valid actions: {[a.value for a in TransitionAction if not a.value.startswith('system_')]}"
        )

    # Block system actions from HR endpoint
    if action.value.startswith("system_"):
        raise HTTPException(status_code=400, detail="System actions cannot be triggered manually")

    # Execute FSM transition
    fsm = CandidateStateMachine(db)
    try:
        logger.debug(f"/api/auth/me user_id={current_user.id}, role={current_user.role}")
        result = fsm.transition(
            application=application,
            action=action,
            user_id=current_user.id,
            notes=status_update.hr_notes,
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except DuplicateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle HR notes
    if status_update.hr_notes:
        application.hr_notes = status_update.hr_notes

    # ─── Post-transition side effects ───────────────────────────────────
    raw_access_key = None

    if action == TransitionAction.APPROVE_FOR_INTERVIEW:
        # Create or refresh interview record + access key
        raw_access_key = _ensure_interview_record(application, db)

    if action == TransitionAction.HIRE:
        # Create HiringDecision record
        from app.domain.models import HiringDecision
        existing = db.query(HiringDecision).filter(
            HiringDecision.application_id == application_id
        ).first()
        if not existing:
            decision = HiringDecision(
                application_id=application_id,
                hr_id=current_user.id,
                decision="hired",
                decision_comments=status_update.hr_notes or "Hired via pipeline",
                decided_at=datetime.now(timezone.utc),
            )
            db.add(decision)

    if action == TransitionAction.REJECT:
        from app.domain.models import HiringDecision
        existing = db.query(HiringDecision).filter(
            HiringDecision.application_id == application_id
        ).first()
        if not existing:
            decision = HiringDecision(
                application_id=application_id,
                hr_id=current_user.id,
                decision="rejected",
                decision_comments=status_update.hr_notes or "Rejected via pipeline",
                decided_at=datetime.now(timezone.utc),
            )
            db.add(decision)
    # ────────────────────────────────────────────────────────────────────

    # Atomic commit
    try:
        db.commit()
        db.refresh(application)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save state transition")

    # ─── Email triggers (ONLY after successful commit) ──────────────────
    candidate_email = application.candidate_email
    job_title = application.job.title

    logger.info(
        f"EMAIL_TRIGGER_CHECK: app={application.id}, "
        f"email_type={result.email_type}, "
        f"raw_access_key_exists={raw_access_key is not None}, "
        f"candidate_email={candidate_email}"
    )

    if result.email_type == "approved_for_interview" and raw_access_key:
        logger.info(f"[EMAIL] Scheduling approved_for_interview email to {candidate_email}")
        background_tasks.add_task(send_approved_for_interview_email, candidate_email, job_title, raw_access_key)
    elif result.email_type == "rejected":
        logger.info(f"[EMAIL] Scheduling rejected email to {candidate_email}")
        background_tasks.add_task(send_rejected_email, candidate_email, job_title, False)
    elif result.email_type == "call_for_interview":
        logger.info(f"[EMAIL] Scheduling call_for_interview email to {candidate_email}")
        from app.services.email_service import send_call_for_interview_email
        background_tasks.add_task(send_call_for_interview_email, candidate_email, job_title)
    elif result.email_type == "hired":
        logger.info(f"[EMAIL] Scheduling hired email to {candidate_email}")
        from app.services.email_service import send_hired_email
        background_tasks.add_task(send_hired_email, candidate_email, job_title, application.interview)
    elif result.email_type:
        logger.warning(f"[EMAIL] No email trigger matched for email_type={result.email_type}")
    # ────────────────────────────────────────────────────────────────────

    return {
        "id": application.id,
        "status": application.status,
        "transition": {
            "from_state": result.from_state,
            "to_state": result.to_state,
            "action": result.action,
            "email_type": result.email_type,
        }
    }


def _ensure_interview_record(application: Application, db) -> str:
    """Create or refresh Interview record + access key for an application."""
    import uuid
    raw_access_key = secrets.token_urlsafe(16)
    hashed_key = pwd_context.hash(raw_access_key)
    expiration = datetime.now(timezone.utc) + timedelta(hours=24)

    existing_interview = db.query(Interview).filter(
        Interview.application_id == application.id
    ).first()

    if not existing_interview:
        interview_stage = 'aptitude' if application.job.aptitude_enabled else 'first_level'
        unique_test_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"

        new_interview = Interview(
            test_id=unique_test_id,
            application_id=application.id,
            status='not_started',
            access_key_hash=hashed_key,
            expires_at=expiration,
            is_used=False,
            interview_stage=interview_stage,
        )
        db.add(new_interview)
    elif existing_interview.status == 'not_started':
        existing_interview.access_key_hash = hashed_key
        existing_interview.expires_at = expiration
        if not existing_interview.test_id:
            existing_interview.test_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"

    return raw_access_key

@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """
    Delete an application along with associated data. HR only.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    validate_hr_ownership(app, current_user, resource_name="application")

    try:
        db.delete(app)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting application {application_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete application. It might have complex dependencies.")
    return {"message": "Application deleted successfully"}

@router.post("/{application_id}/merge/{target_id}")
async def merge_applications(
    application_id: int,
    target_id: int,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """
    Merge a source application into a target application.
    Used for resolving duplicate submissions.
    """
    source = db.query(Application).filter(Application.id == application_id).first()
    target = db.query(Application).filter(Application.id == target_id).first()
    
    if not source or not target:
        raise HTTPException(status_code=404, detail="One or both applications not found")
    validate_hr_ownership(source, current_user, resource_name="application")
    validate_hr_ownership(target, current_user, resource_name="application")
        
    if source.job_id != target.job_id:
        raise HTTPException(status_code=400, detail="Applications must belong to the same job to be merged")
        
    # Merge strategy: Target keeps its identity, but takes scores/notes from source if they are better
    try:
        if source.resume_score > (target.resume_score or 0):
            target.resume_score = source.resume_score
            
        target.hr_notes = (target.hr_notes or "") + f"\n[MERGED from App #{application_id}]: " + (source.hr_notes or "No notes")
        
        # Log the merge
        from app.domain.models import AuditLog
        merge_log = AuditLog(
            user_id=current_user.id,
            action="APPLICATION_MERGED",
            resource_type="Application",
            resource_id=target.id,
            details=json.dumps({"source_id": application_id, "target_id": target_id})
        )
        db.add(merge_log)
        
        # Mark source as rejected/duplicate and hide it or delete it
        source.status = "rejected"
        source.hr_notes = (source.hr_notes or "") + f"\n[MERGED INTO App #{target_id}]"
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Merge error: {e}")
        raise HTTPException(status_code=500, detail="Failed to merge applications")
        
    return {"status": "success", "message": f"Application {application_id} merged into {target_id}"}
@router.put("/{application_id}/notes", response_model=ApplicationResponse)
async def update_hr_notes(
    application_id: int,
    notes_update: ApplicationNotesUpdate,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db)
):
    """Update HR notes for an application"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    validate_hr_ownership(application, current_user, resource_name="application")
        
    application.hr_notes = notes_update.hr_notes
    db.commit()
    db.refresh(application)
    return application

@router.post("/extract-basic-info")
async def extract_basic_info(resume_file: UploadFile = File(...)):
    """Fast endpoint to extract Name and Phone from an uploaded resume."""
    # Read file content
    content = await resume_file.read()
    
    # Extract text locally in memory
    resume_text = ""
    file_ext = resume_file.filename.lower().split('.')[-1]
    
    try:
        if file_ext == 'pdf':
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            for page in reader.pages:
                resume_text += page.extract_text() + "\n"
        elif file_ext in ['docx', 'doc']:
            import docx
            import io
            doc = docx.Document(io.BytesIO(content))
            for para in doc.paragraphs:
                resume_text += para.text + "\n"
        else:
            resume_text = content.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.error(f"Error extracting text for basic info: {e}")
        return {"name": "", "phone": ""}
        
    if not resume_text.strip():
        return {"name": "", "phone": ""}
        
    info = await extract_basic_candidate_info(resume_text)
    # Privacy & correctness: never return or pre-fill email here.
    # Only expose minimal fields required for UX pre-fill.
    return {
        "name": info.get("name") if isinstance(info, dict) else "",
        "phone": info.get("phone") if isinstance(info, dict) else "",
    }
