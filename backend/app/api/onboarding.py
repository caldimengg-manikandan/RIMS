from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, UploadFile, File
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.infrastructure.database import get_db
from app.domain.models import User, Application, GlobalSettings, Notification
from app.domain.schemas import ApplicationResponse, OfferResponseRequest
from app.core.auth import get_current_hr, get_current_admin
from app.services.offer_letter_service import generate_offer_letter_pdf, get_offer_letter_data
from app.services.email_service import send_offer_letter_email, send_simple_email
from app.core.config import get_settings
from typing import List, Optional
import os
import uuid
import logging
import json
import random
import string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from fastapi.responses import FileResponse, RedirectResponse
from io import BytesIO
from app.core.storage import upload_file, get_signed_url, get_public_url, get_supabase_client

import secrets
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])
settings = get_settings()

# Point 6: Lightweight Rate Limiting (Simple In-Memory)
RATE_LIMIT_STORAGE = defaultdict(list)
MAX_REQUESTS_PER_MIN = 10

def rate_limit(ip: str):
    now = time.time()
    RATE_LIMIT_STORAGE[ip] = [t for t in RATE_LIMIT_STORAGE[ip] if now - t < 60]
    if len(RATE_LIMIT_STORAGE[ip]) >= MAX_REQUESTS_PER_MIN:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    RATE_LIMIT_STORAGE[ip].append(now)

def generate_short_id():
    """Point 1: Secure URL-safe short IDs."""
    return secrets.token_urlsafe(8)

async def get_application_by_short_id(db: Session, short_id: str, lock=False):
    """Secure lookup: short_id -> Application."""
    query = db.query(Application).filter(Application.offer_short_id == short_id)
    if lock:
        query = query.with_for_update()
    return query.first()

from app.services.state_machine import CandidateStateMachine, TransitionAction, CandidateState

def log_audit(db: Session, action: str, application_id: int, user_id: Optional[int], details: dict, ip: Optional[str] = None, is_critical: bool = False):
    """Helper to record system events in AuditLog table."""
    from app.domain.models import AuditLog
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type="Application",
            resource_id=application_id,
            details=json.dumps(details),
            ip_address=ip,
            is_critical=is_critical
        )
        db.add(log)
        # Flush to DB but don't commit (let parent manage transaction)
        db.flush()
    except Exception as e:
        logger.error(f"Audit log failed: {e}")

@router.get("/candidates", response_model=List[ApplicationResponse])
def get_onboarding_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """Fetch candidates in onboarding pipeline."""
    from sqlalchemy.orm import joinedload
    from app.domain.models import Job
    
    query = db.query(Application).filter(
        Application.status.in_(["hired", "pending_approval", "offer_sent", "accepted", "onboarded"])
    )
    
    # ── Phase 6: Enforce ownership at API level ──
    if current_user.role != "super_admin":
        query = query.outerjoin(Job).filter(
            or_(Application.hr_id == current_user.id, Job.hr_id == current_user.id)
        )
    else:
        # For admin consistency, ensure we outerjoin Job for relationship loading
        query = query.outerjoin(Job)
        
    # Eager load relationships for UI consistency (Phase 8)
    candidates = query.options(joinedload(Application.job)).all()
    return candidates

@router.post("/applications/{application_id}/send-offer")
async def request_offer_approval(
    application_id: int,
    joining_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """Stage offer for approval. Status moves to PENDING_APPROVAL."""
    application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # State Machine Hardening
    from app.services.state_machine import CandidateStateMachine, TransitionAction
    fsm = CandidateStateMachine(db)
    try:
        fsm.transition(application, TransitionAction.SEND_FOR_APPROVAL, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if application.offer_sent:
        raise HTTPException(status_code=400, detail="Offer letter already sent")

    # Validation Layer
    if not application.candidate_email:
        raise HTTPException(status_code=400, detail="Candidate email is missing")

    settings_records = db.query(GlobalSettings).all()
    gs = {s.key: s.value for s in settings_records}
    
    try:
        jdate = datetime.fromisoformat(joining_date.replace('Z', '+00:00'))
    except:
        raise HTTPException(status_code=400, detail="Invalid joining date format")

    # Update DB for approval flow
    application.status = "pending_approval"
    application.offer_approval_status = "pending"
    application.joining_date = jdate
    application.offer_template_snapshot = gs.get("offer_letter_template")
    
    # Secure Token & Short ID (Point 1)
    application.offer_token = str(uuid.uuid4())
    application.offer_short_id = generate_short_id()
    application.offer_token_expiry = datetime.now(timezone.utc) + timedelta(days=7)
    application.offer_token_used = False
    
    db.add(application)
    # log_audit no longer commits internally in my next step
    log_audit(db, "OFFER_STAGED", application.id, current_user.id, {"joining_date": joining_date}, is_critical=True)

    # Notify Super Admins
    super_admins = db.query(User).filter(User.role == "super_admin").all()
    for admin in super_admins:
        notif = Notification(
            user_id=admin.id,
            notification_type="OFFER_PENDING",
            title="Offer Approval Required",
            message=f"HR {current_user.full_name} has requested approval for {application.candidate_name}'s offer letter.",
            related_application_id=application.id
        )
        db.add(notif)
    
    db.commit()
    return {"status": "success", "message": "Offer letter staged for approval"}

@router.post("/applications/{application_id}/approve-offer")
async def approve_offer_letter(
    application_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Admin approves the offer. Only SUPER_ADMIN allowed."""
    application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # State Machine Hardening
    from app.services.state_machine import CandidateStateMachine, TransitionAction
    fsm = CandidateStateMachine(db)
    try:
        fsm.transition(application, TransitionAction.SEND_OFFER, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    settings_records = db.query(GlobalSettings).all()
    gs = {s.key: s.value for s in settings_records}
    
    # PDF Generation (In-memory to Supabase)
    try:
        from io import BytesIO
        from xhtml2pdf import pisa
        from jinja2 import Template
        
        filename = f"offer_{application.id}_{int(datetime.now().timestamp())}.pdf"
        storage_path = f"generated_offers/{filename}"
        
        data = get_offer_letter_data(
            candidate_name=application.candidate_name,
            job_role=application.job.title if application.job else "N/A",
            department=(application.job.domain if application.job else "Engineering") or "Engineering",
            joining_date=application.joining_date,
            company_name=gs.get("company_name", "Our Company"),
            logo_url=gs.get("company_logo_url", ""),
            hr_email=gs.get("hr_email", ""),
            hr_name=gs.get("hr_name", ""),
            hr_phone=gs.get("hr_phone", ""),
            company_address=gs.get("company_address", "")
        )
        
        template = Template(application.offer_template_snapshot)
        rendered_html = template.render(**data)
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(rendered_html, dest=pdf_buffer)
        
        pdf_buffer.seek(0)

        # Save PDF to a local temp file so the email task can attach it
        import tempfile
        pdf_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "offer_pdfs")
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_local_path = os.path.join(pdf_dir, filename)
        with open(pdf_local_path, "wb") as f:
            f.write(pdf_buffer.read())

        application.offer_pdf_path = pdf_local_path
        logger.info(f"Offer PDF generated and saved: {pdf_local_path}")
    except Exception as e:
        logger.error(f"Offer PDF error: {e}")
        log_audit(db, "OFFER_PDF_FAILED", application.id, current_user.id, {"error": str(e)})
        raise HTTPException(status_code=500, detail="Document generation failure. Process aborted.")

    # Update Application State
    application.offer_sent = True
    application.offer_sent_date = datetime.now(timezone.utc)
    application.offer_approval_status = "approved"
    application.offer_approved_by = current_user.id
    application.offer_approved_at = datetime.now(timezone.utc)
    application.offer_email_status = "pending"
    
    db.add(application)
    
    # Composite transaction: Status + Audit + Notifications (Phase 8 Fix)
    # Status and Audit are handled by fsm.transition earlier, just updating extra fields here.

    # Notify HR
    if application.hr_id:
        db.add(Notification(
            user_id=application.hr_id,
            notification_type="OFFER_APPROVED",
            title="Offer Approved",
            message=f"Offer letter for {application.candidate_name} has been approved.",
            related_application_id=application.id
        ))

    db.commit()

    background_tasks.add_task(process_offer_email, application.id, application.offer_pdf_path, gs.get("company_name", "Our Company"))
    return {"status": "success", "message": "Offer letter approved and email triggered"}

async def process_offer_email(application_id: int, storage_path: str, company_name: str):
    """Internal task with email-safe short links (Point 1)."""
    from app.infrastructure.database import SessionLocal
    db = SessionLocal()
    try:
        application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
        if not application or application.offer_email_status == "sent": return

        final_path = application.offer_pdf_path or storage_path
        
        # Link Safety: Use Short ID (Point 1)
        base_url = settings.frontend_base_url 
        accept_link = f"{base_url}/offer/respond?ref={application.offer_short_id}&intent=accept"
        reject_link = f"{base_url}/offer/respond?ref={application.offer_short_id}&intent=reject"

        await send_offer_letter_email(
            to_email=application.candidate_email,
            candidate_name=application.candidate_name,
            company_name=company_name,
            offer_letter_path=final_path,
            accept_link=accept_link,
            reject_link=reject_link
        )
        
        application.offer_email_status = "sent"
        db.commit()
        log_audit(db, "OFFER_EMAIL_SENT", application.id, None, {"recipient": application.candidate_email})
        
    except Exception as e:
        logger.error(f"Email failed: {e}")
        application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
        if application:
            application.offer_email_status = "failed"
            application.offer_email_retry_count += 1
            db.commit()
            log_audit(db, "OFFER_EMAIL_FAILED", application_id, None, {"error": str(e)})
    finally:
        db.close()

@router.get("/offer")
async def get_offer_preview(request: Request, ref: str, db: Session = Depends(get_db)):
    """Public preview with short_id support & rate limiting (Point 1 & 6)."""
    rate_limit(request.client.host if request.client else "unknown")
    application = await get_application_by_short_id(db, ref)
    if not application:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    if application.offer_token_used:
        raise HTTPException(status_code=400, detail="Offer already responded to.")
    
    if application.offer_token_expiry and application.offer_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Offer expired.")

    return {
        "candidate_name": application.candidate_name,
        "job_title": application.job.title,
        "joining_date": application.joining_date.isoformat(),
        "company_name": db.query(GlobalSettings).filter(GlobalSettings.key == "company_name").first().value or "Our Company"
    }

def generate_employee_id(db: Session):
    """Utility to generate a unique employee ID (Task 8)."""
    while True:
        emp_id = 'EMP-' + ''.join(random.choices(string.digits, k=6))
        exists = db.query(Application).filter(Application.employee_id == emp_id).first()
        if not exists:
            return emp_id

@router.post("/applications/{application_id}/capture-photo")
async def capture_photo(
    application_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """Save captured webcam photo for onboarded candidate to Supabase (Task 7)."""
    application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.status != "onboarded":
        raise HTTPException(status_code=400, detail="Photo capture only allowed for onboarded candidates.")

    try:
        content = await photo.read()
        filename = f"photo_{application_id}_{int(time.time())}.jpg"
        storage_path = f"{application_id}/{filename}"
        
        upload_file(settings.supabase_bucket_id_photos, storage_path, content, content_type="image/jpeg")
            
        application.candidate_photo_path = storage_path
        
        from app.services.candidate_service import CandidateService
        CandidateService(db).create_audit_log(current_user.id, "PHOTO_CAPTURED", "Application", application_id, {"storage_path": storage_path})
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Cloud photo save failed: {e}")
        raise HTTPException(status_code=500, detail=f"Photo save failed: {str(e)}")
        
    return {"status": "success", "candidate_photo_path": application.candidate_photo_path}

@router.post("/applications/{application_id}/generate-id-card")
def generate_id_card(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """Generate ID Card PDF with photo and employee details (Task 8)."""
    application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if not application.candidate_photo_path:
        raise HTTPException(status_code=400, detail="Cannot generate ID card without photo capture.")

    # 1. Generate unique Employee ID if not exists
    if not application.employee_id:
        from app.services.candidate_service import CandidateService
        application.employee_id = generate_employee_id(db)

    # 2. PDF Generation with ReportLab in-memory
    try:
        packet = BytesIO()
        # ID Card Dimensions (Credit Card Size aprox 3.375 x 2.125 inches)
        # We'll use 4x3 for a clear large card
        c = canvas.Canvas(packet, pagesize=(4*inch, 3*inch))
        
        # Draw Border
        c.setStrokeColorRGB(0.1, 0.1, 0.4)
        c.rect(0.1*inch, 0.1*inch, 3.8*inch, 2.8*inch, stroke=1, fill=0)
        
        # Header / Company Name
        settings_dict = {s.key: s.value for s in db.query(GlobalSettings).all()}
        company_name = settings_dict.get("company_name", "RIMS RECRUITMENT")
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(2*inch, 2.6*inch, company_name)
        
        # Draw Photo from Supabase
        try:
            supabase = get_supabase_client()
            photo_bytes = supabase.storage.from_(settings.supabase_bucket_id_photos).download(application.candidate_photo_path)
            if photo_bytes:
                img_stream = BytesIO(photo_bytes)
                from reportlab.lib.utils import ImageReader
                c.drawImage(ImageReader(img_stream), 0.2*inch, 0.8*inch, width=1.2*inch, height=1.4*inch)
            else:
                c.rect(0.2*inch, 0.8*inch, 1.2*inch, 1.4*inch, stroke=1)
                c.setFont("Helvetica", 8)
                c.drawString(0.3*inch, 1.5*inch, "PHOTO MISSING")
        except Exception as e:
            logger.error(f"Error fetching photo for ID card: {e}")
            c.rect(0.2*inch, 0.8*inch, 1.2*inch, 1.4*inch, stroke=1)
            c.setFont("Helvetica", 8)
            c.drawString(0.3*inch, 1.5*inch, "FETCH ERROR")

        # Details
        c.setFont("Helvetica-Bold", 10)
        c.drawString(1.5*inch, 2.0*inch, f"NAME: {application.candidate_name}")
        c.setFont("Helvetica", 10)
        c.drawString(1.5*inch, 1.8*inch, f"ID: {application.employee_id}")
        c.drawString(1.5*inch, 1.6*inch, f"ROLE: {application.job.title if application.job else 'N/A'}")
        c.drawString(1.5*inch, 1.4*inch, f"DEPT: {(application.job.domain if application.job else 'Engineering') or 'HR'}")
        c.drawString(1.5*inch, 1.2*inch, f"JOINING: {application.joining_date.strftime('%Y-%m-%d') if application.joining_date else 'N/A'}")
        
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(2*inch, 0.3*inch, "This card is company property. If found return to HR.")
        
        c.showPage()
        c.save()
        
        # Upload to Supabase
        filename = f"id_card_{application.employee_id}.pdf"
        storage_path = f"{application_id}/{filename}"
        packet.seek(0)
        returned_path = upload_file(settings.supabase_bucket_id_cards, storage_path, packet.read(), content_type="application/pdf")
        
        application.id_card_url = returned_path
        from app.services.candidate_service import CandidateService
        CandidateService(db).create_audit_log(current_user.id, "ID_CARD_GENERATED", "Application", application_id, {"employee_id": application.employee_id})
        db.commit()
        
        return {"status": "success", "id_card_url": application.id_card_url, "employee_id": application.employee_id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"ID Card Generation Error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@router.get("/applications/{application_id}/download-id-card")
def download_id_card(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """Generate a Signed URL for the generated ID card PDF (Task 8)."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application or not application.id_card_url:
        raise HTTPException(status_code=404, detail="ID Card not found")
        
    signed_url = get_signed_url(settings.supabase_bucket_id_cards, application.id_card_url)
    if not signed_url:
        raise HTTPException(status_code=500, detail="Failed to generate download link")
        
    return RedirectResponse(url=signed_url)

@router.post("/respond")
async def respond_to_offer(request: Request, response_req: OfferResponseRequest, db: Session = Depends(get_db)):
    """Public response with Row Locking & Short ID support (Point 1, 2, 6)."""
    rate_limit(request.client.host if request.client else "unknown")
    
    # Use Short ID lookup with ROW LOCKING (Point 2)
    application = await get_application_by_short_id(db, response_req.token, lock=True)
    if not application:
        raise HTTPException(status_code=404, detail="Reference ID not found")
    
    if application.offer_token_used:
         raise HTTPException(status_code=400, detail="Response already processed. Access locked.")
    
    now = datetime.now(timezone.utc)
    target_action = TransitionAction.ACCEPT_OFFER if response_req.response_type == "accept" else TransitionAction.REJECT
    
    from app.services.state_machine import CandidateStateMachine
    fsm = CandidateStateMachine(db)
    try:
        fsm.transition(application, target_action)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    application.offer_token_used = True
    application.offer_response_status = response_req.response_type
    application.offer_response_date = now
    application.offer_accepted_ip = client_ip
    application.offer_accepted_user_agent = user_agent
    
    # Combined transaction (Phase 8 Fix)
    log_audit(db, f"OFFER_{response_req.response_type.upper()}", application.id, None, {
        "ip": client_ip,
        "ua": user_agent
    }, ip=client_ip, is_critical=True)

    db.commit() # Atomic release of lock

    return {"status": "success"}

@router.post("/bulk/request-approval")
async def bulk_request_approval(
    application_ids: List[int],
    joining_date: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """Bulk stage offers."""
    results = {"success": [], "failed": []}
    for app_id in application_ids:
        try:
            await request_offer_approval(app_id, joining_date, db, current_user)
            results["success"].append(app_id)
        except Exception as e:
            results["failed"].append({"id": app_id, "error": str(e)})
    return results

@router.post("/bulk/approve")
async def bulk_approve_offers(
    application_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Bulk approve offers."""
    results = {"success": [], "failed": []}
    for app_id in application_ids:
        try:
            await approve_offer_letter(app_id, background_tasks, db, current_user)
            results["success"].append(app_id)
        except Exception as e:
            results["failed"].append({"id": app_id, "error": str(e)})
    return results

@router.get("/analytics/offers")
def get_offer_analytics(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Recomputed Analytics from Audit Logs (Point 4)."""
    from app.domain.models import AuditLog
    
    total_approved = db.query(AuditLog).filter(AuditLog.action == "OFFER_APPROVED").count()
    total_accepted = db.query(AuditLog).filter(AuditLog.action == "OFFER_ACCEPTED").count()
    total_rejected = db.query(AuditLog).filter(AuditLog.action == "OFFER_REJECTED").count()
    
    # Calculate response times from Audit Log flow
    sent_logs = db.query(AuditLog).filter(AuditLog.action == "OFFER_APPROVED").all()
    resp_logs = db.query(AuditLog).filter(AuditLog.action.in_(["OFFER_ACCEPTED", "OFFER_REJECTED"])).all()
    
    resp_map = {log.resource_id: log.created_at for log in resp_logs}
    time_diffs = []
    for s_log in sent_logs:
        if s_log.resource_id in resp_map:
            diff = (resp_map[s_log.resource_id] - s_log.created_at).total_seconds()
            time_diffs.append(diff)
            
    avg_hours = (sum(time_diffs) / len(time_diffs) / 3600) if time_diffs else 0

    return {
        "total_offers_approved": total_approved,
        "acceptance_rate": (total_accepted / total_approved * 100) if total_approved > 0 else 0,
        "rejection_rate": (total_rejected / total_approved * 100) if total_approved > 0 else 0,
        "avg_response_time_hours": avg_hours,
        "source": "audit_logs"
    }

@router.post("/applications/{application_id}/onboard")
def complete_onboarding(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_hr)
):
    """Mark candidate as onboarded manually with transition guard."""
    application = db.query(Application).filter(Application.id == application_id).with_for_update().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    from app.services.state_machine import CandidateStateMachine, TransitionAction
    fsm = CandidateStateMachine(db)
    try:
        fsm.transition(application, TransitionAction.SYSTEM_ONBOARD, user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    application.onboarded_at = datetime.now(timezone.utc)
    
    log_audit(db, "ONBOARDED_MANUAL", application.id, current_user.id, {"status": "success"}, is_critical=True)
    db.commit()
    return {"status": "success"}

@router.post("/cron/check-arrivals")
def check_candidate_arrivals(db: Session = Depends(get_db)):
    """
    (System/Admin) Auto-transition candidates to 'onboarded' if joining date is today.
    Task 2 Requirement.
    """
    from app.services.state_machine import CandidateState
    today = datetime.now(timezone.utc).date()
    
    # Range check for the whole day
    start_of_day = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_of_day = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Find candidates who accepted offer and join today
    candidates = db.query(Application).filter(
        Application.status == "accepted",
        Application.joining_date >= start_of_day,
        Application.joining_date <= end_of_day
    ).all()
    
    onboarded_count = 0
    for app in candidates:
        app.status = "onboarded"
        app.onboarded_at = datetime.now(timezone.utc)
        
        log_audit(db, "SYSTEM_AUTO_ONBOARD", app.id, None, {"reason": "Joining date reached"}, is_critical=True)
        
        # Notify HR
        if app.hr_id:
             db.add(Notification(
                 user_id=app.hr_id,
                 notification_type="CANDIDATE_ARRIVED",
                 title="Candidate Joined",
                 message=f"{app.candidate_name} has joined today. Capture photo and generate ID card.",
                 related_application_id=app.id
             ))
        onboarded_count += 1
        
    db.commit()
    return {"status": "success", "onboarded_count": onboarded_count}
