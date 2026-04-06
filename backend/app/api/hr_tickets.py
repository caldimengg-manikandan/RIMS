from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.infrastructure.database import get_db
from app.domain.schemas import InterviewIssueResponse
from app.domain.models import User
from app.core.auth import get_current_hr

# Reuse existing implementation to avoid schema drift
from app.api.tickets import get_tickets as _get_tickets


router = APIRouter(prefix="/api/hr", tags=["HR Tickets"])


@router.get("/tickets", response_model=List[InterviewIssueResponse])
def hr_get_tickets(
    status: str = "pending",
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_hr),
    db: Session = Depends(get_db),
):
    """
    Alias endpoint for HR tickets dashboard.
    Non-breaking: returns the exact same schema as GET /api/tickets.
    """
    return _get_tickets(status=status, skip=skip, limit=limit, current_user=current_user, db=db)

