from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.domain.models import User
from app.infrastructure.database import get_db

settings = get_settings()
logger = logging.getLogger(__name__)

# Dummy pwd_context for backwards compatibility, only providing what is strictly tested if any
class _DummyPwdContext:
    def verify(self, plain, hashed):
        return verify_password(plain, hashed)
pwd_context = _DummyPwdContext()

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash password using direct bcrypt to avoid passlib crashes"""
    pwd_bytes = password[:72].encode('utf-8')
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode('ascii')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash directly with bcrypt"""
    try:
        pwd_bytes = plain_password[:72].encode('utf-8')
        hash_bytes = hashed_password.encode('ascii')
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)
    user_id: int = int(payload.get("sub"))
    role: str = payload.get("role")
    
    if user_id is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_hr(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is HR or Admin (Enterprise Roles)"""
    if current_user.role not in ["admin", "hr_manager", "recruiter", "hr"]: # Keeping 'hr' for legacy support
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Role-based access restriction."
        )
    return current_user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure user is Admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins can access this resource"
        )
    return current_user

def require_roles(allowed_roles: list[str]):
    """Dynamic Role-Based Access Control (RBAC) dependency factory"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles and "admin" not in allowed_roles: # Admins typically override
            if current_user.role != "admin": # Explicit admin check if admin isn't in allowed list but should bypass
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Requires one of {allowed_roles}"
                )
        return current_user
    return role_checker

def get_current_interview(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Dependency to get current authenticated interview session"""
    from app.domain.models import Interview
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload.get("role") != "interview":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid interview credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    interview_id = int(payload.get("sub"))
    
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if interview.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This interview has already been completed",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if interview.status == "terminated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This interview was terminated due to a policy violation",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if interview.status == "not_started":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Interview has not been started yet. Please use the access key to start it.",
        )
        
    if interview.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Interview session is no longer active (Status: {interview.status})",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return interview
