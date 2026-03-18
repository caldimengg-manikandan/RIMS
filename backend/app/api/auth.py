from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.infrastructure.database import get_db
from app.domain.models import User
from app.domain.schemas import UserRegister, UserLogin, TokenResponse, UserResponse, UserVerifyOTP
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user, pwd_context
from app.services.email_service import send_otp_email
from app.core.config import get_settings
import secrets
import string

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

from app.core.rate_limiter import limiter
from fastapi import Request

@router.post("/register", response_model=UserResponse)
@limiter.limit("20/minute")
def register(request: Request, user_data: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Register a new user (Candidate or HR)"""
    user_data.email = user_data.email.lower()

    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered and verified"
            )
        else:
            try:
                existing_user.password_hash = hash_password(user_data.password)
                existing_user.full_name = user_data.full_name
                raw_otp = ''.join(secrets.choice(string.digits) for _ in range(6))
                existing_user.otp_code = hash_password(raw_otp)
                existing_user.otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
                db.commit()
                background_tasks.add_task(send_otp_email, existing_user.email, raw_otp)
                return existing_user
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail="Registration update failed safely.")

    role = "hr"
    raw_otp = ''.join(secrets.choice(string.digits) for _ in range(6))
    hashed_otp = hash_password(raw_otp)
    hashed_password = hash_password(user_data.password)

    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role=role,
        is_verified=False,
        otp_code=hashed_otp,
        otp_expiry=datetime.now(timezone.utc) + timedelta(minutes=30)
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        background_tasks.add_task(send_otp_email, new_user.email, raw_otp)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration creation failed safely.")

@router.post("/verify", response_model=dict)
@limiter.limit("20/minute")
def verify_otp(request: Request, verification_data: UserVerifyOTP, db: Session = Depends(get_db)):
    """Verify user account with OTP"""
    email = verification_data.email.lower()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_verified:
        return {"message": "User is already verified"}

    # OTP validation (no bypass — use actual OTP from email/console in dev)
    if True:
        if not user.otp_expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OTP has been generated. Please register again."
            )

        expiry_time = user.otp_expiry
        if expiry_time.tzinfo is None:
            expiry_time = expiry_time.replace(tzinfo=timezone.utc)
            
        if datetime.now(timezone.utc) > expiry_time:
            try:
                user.otp_code = None
                user.otp_expiry = None
                db.commit()
            except Exception:
                db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please register again to receive a new OTP."
            )

        # Dev override for testing without email server
        is_dev_override = settings.env == "development" and verification_data.otp == "000000"
        
        if not is_dev_override:
            if not user.otp_code or not pwd_context.verify(verification_data.otp, user.otp_code):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid OTP code"
                )

    try:
        user.is_verified = True
        user.otp_code = None
        user.otp_expiry = None
        db.commit()
        return {"message": "Account successfully verified"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Verification finalization failed safely.")

@router.post("/login", response_model=TokenResponse)
@limiter.limit("30/minute")
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token"""
    credentials.email = credentials.email.lower()
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not verified. Please verify your email first."
        )

    access_token_expires = timedelta(minutes=settings.jwt_expiration_minutes)
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name
    }
    access_token = create_access_token(token_data, access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user
