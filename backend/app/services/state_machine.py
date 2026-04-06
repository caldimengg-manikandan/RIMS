"""
Candidate State Machine — Single Source of Truth

This module implements a strict finite state machine for candidate pipeline
transitions. Every state change in the system MUST go through this module.

Design principles:
  1. Every state has explicit allowed transitions
  2. Invalid transitions are impossible (raise errors)
  3. State changes are atomic (single DB commit)
  4. State history is logged to StateTransitionLog
  5. Emails trigger ONLY after a successful state transition
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.domain.models import Application, Job, AuditLog

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. State & Action Enums
# ─────────────────────────────────────────────────────────────────────────────

class CandidateState(str, Enum):
    APPLIED = "applied"
    APTITUDE_ROUND = "aptitude_round"
    AI_INTERVIEW = "ai_interview"
    AI_INTERVIEW_COMPLETED = "ai_interview_completed"
    REVIEW_LATER = "review_later"
    PHYSICAL_INTERVIEW = "physical_interview"
    HIRED = "hired"
    REJECTED = "rejected"


class TransitionAction(str, Enum):
    """Actions that trigger state transitions."""
    APPROVE_FOR_INTERVIEW = "approve_for_interview"
    REJECT = "reject"
    CALL_FOR_INTERVIEW = "call_for_interview"
    REVIEW_LATER = "review_later"
    HIRE = "hire"
    # System-initiated (automatic)
    SYSTEM_APTITUDE_COMPLETE = "system_aptitude_complete"
    SYSTEM_INTERVIEW_COMPLETE = "system_interview_complete"


# Terminal states — no transitions out of these
TERMINAL_STATES = frozenset({CandidateState.HIRED, CandidateState.REJECTED})


# ─────────────────────────────────────────────────────────────────────────────
# 2. Transition Table
# ─────────────────────────────────────────────────────────────────────────────

# Key: (current_state, action) → target_state
# Some transitions are dynamic (APPROVE depends on job config), handled in code.

_TRANSITION_TABLE: Dict[Tuple[CandidateState, TransitionAction], CandidateState] = {
    # applied
    # APPROVE_FOR_INTERVIEW is dynamic — see _resolve_approve_target()
    (CandidateState.APPLIED, TransitionAction.REJECT): CandidateState.REJECTED,

    # aptitude_round
    (CandidateState.APTITUDE_ROUND, TransitionAction.SYSTEM_APTITUDE_COMPLETE): CandidateState.AI_INTERVIEW,
    (CandidateState.APTITUDE_ROUND, TransitionAction.REJECT): CandidateState.REJECTED,

    # ai_interview
    (CandidateState.AI_INTERVIEW, TransitionAction.SYSTEM_INTERVIEW_COMPLETE): CandidateState.AI_INTERVIEW_COMPLETED,
    (CandidateState.AI_INTERVIEW, TransitionAction.REJECT): CandidateState.REJECTED,

    # ai_interview_completed
    (CandidateState.AI_INTERVIEW_COMPLETED, TransitionAction.CALL_FOR_INTERVIEW): CandidateState.PHYSICAL_INTERVIEW,
    (CandidateState.AI_INTERVIEW_COMPLETED, TransitionAction.REVIEW_LATER): CandidateState.REVIEW_LATER,
    (CandidateState.AI_INTERVIEW_COMPLETED, TransitionAction.REJECT): CandidateState.REJECTED,

    # review_later
    (CandidateState.REVIEW_LATER, TransitionAction.CALL_FOR_INTERVIEW): CandidateState.PHYSICAL_INTERVIEW,
    (CandidateState.REVIEW_LATER, TransitionAction.REJECT): CandidateState.REJECTED,

    # physical_interview
    (CandidateState.PHYSICAL_INTERVIEW, TransitionAction.HIRE): CandidateState.HIRED,
    (CandidateState.PHYSICAL_INTERVIEW, TransitionAction.REJECT): CandidateState.REJECTED,
}

# Email mapping: target_state → email_type identifier
EMAIL_TRIGGERS: Dict[Tuple[TransitionAction, CandidateState], str] = {
    (TransitionAction.APPROVE_FOR_INTERVIEW, CandidateState.APTITUDE_ROUND): "approved_for_interview",
    (TransitionAction.APPROVE_FOR_INTERVIEW, CandidateState.AI_INTERVIEW): "approved_for_interview",
    (TransitionAction.REJECT, CandidateState.REJECTED): "rejected",
    (TransitionAction.CALL_FOR_INTERVIEW, CandidateState.PHYSICAL_INTERVIEW): "call_for_interview",
    (TransitionAction.HIRE, CandidateState.HIRED): "hired",
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. State Machine Errors
# ─────────────────────────────────────────────────────────────────────────────

class InvalidTransitionError(Exception):
    """Raised when a requested state transition is not allowed."""
    def __init__(self, current_state: str, action: str, message: str = ""):
        self.current_state = current_state
        self.action = action
        self.message = message or f"Invalid transition: cannot perform '{action}' from state '{current_state}'"
        super().__init__(self.message)


class DuplicateTransitionError(Exception):
    """Raised when attempting a transition to the same state."""
    def __init__(self, state: str):
        self.state = state
        super().__init__(f"Application is already in state '{state}'")


# ─────────────────────────────────────────────────────────────────────────────
# 4. State Machine Service
# ─────────────────────────────────────────────────────────────────────────────

class CandidateStateMachine:
    """
    Strict finite state machine for candidate pipeline transitions.
    
    Usage:
        fsm = CandidateStateMachine(db)
        result = fsm.transition(application, TransitionAction.APPROVE_FOR_INTERVIEW, user_id=hr.id)
        # result.target_state, result.email_type etc.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_allowed_actions(self, application: Application) -> List[str]:
        """Return list of valid actions for the current application state."""
        try:
            current = CandidateState(application.status)
        except ValueError:
            return []

        if current in TERMINAL_STATES:
            return []

        allowed = []
        for (state, action), _target in _TRANSITION_TABLE.items():
            if state == current and not action.value.startswith("system_"):
                allowed.append(action.value)

        # Add dynamic APPROVE action for 'applied' state
        if current == CandidateState.APPLIED:
            allowed.append(TransitionAction.APPROVE_FOR_INTERVIEW.value)

        return sorted(set(allowed))

    def validate_transition(
        self,
        application: Application,
        action: TransitionAction,
    ) -> CandidateState:
        """
        Validate a transition and return the target state.
        Raises InvalidTransitionError if not allowed.
        """
        try:
            current = CandidateState(application.status)
        except ValueError:
            raise InvalidTransitionError(
                application.status, action.value,
                f"Unknown current state: '{application.status}'"
            )

        # Block transitions from terminal states
        if current in TERMINAL_STATES:
            raise InvalidTransitionError(
                current.value, action.value,
                f"Cannot transition from terminal state '{current.value}'"
            )

        # Handle dynamic APPROVE transition
        if action == TransitionAction.APPROVE_FOR_INTERVIEW and current == CandidateState.APPLIED:
            return self._resolve_approve_target(application)

        # Standard table lookup
        key = (current, action)
        if key not in _TRANSITION_TABLE:
            raise InvalidTransitionError(current.value, action.value)

        target = _TRANSITION_TABLE[key]

        # Prevent duplicate transitions
        if current == target:
            raise DuplicateTransitionError(current.value)

        return target

    def transition(
        self,
        application: Application,
        action: TransitionAction,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> "TransitionResult":
        """
        Execute an atomic state transition.
        
        1. Validate the transition
        2. Check action-specific preconditions (e.g. interview completion)
        3. Update application status
        4. Log the transition
        5. Return result with email type
        
        Does NOT commit the transaction — caller must db.commit()
        after handling any additional logic (interview creation, etc.).
        """
        # 1. Validate
        target_state = self.validate_transition(application, action)
        
        # 2. Preconditions (including notes if required)
        self._check_preconditions(application, action, notes)
        
        old_state = application.status

        # 3. Atomic status update
        application.status = target_state.value
        application.updated_at = datetime.now(timezone.utc)

        # 4. Log the transition
        self._log_transition(
            application_id=application.id,
            from_state=old_state,
            to_state=target_state.value,
            action=action.value,
            user_id=user_id,
            notes=notes,
        )

        # 5. Determine email trigger
        email_type = EMAIL_TRIGGERS.get((action, target_state))

        logger.info(
            f"STATE_TRANSITION: app={application.id} "
            f"{old_state} -[{action.value}]-> {target_state.value} "
            f"(user={user_id}, email={email_type})"
        )

        return TransitionResult(
            application_id=application.id,
            from_state=old_state,
            to_state=target_state.value,
            action=action.value,
            email_type=email_type,
        )

    def _check_preconditions(
        self, 
        application: Application, 
        action: TransitionAction, 
        notes: Optional[str] = None
    ):
        """Action-specific guard logic."""
        if action == TransitionAction.APPROVE_FOR_INTERVIEW:
            try:
                cur = CandidateState(application.status)
            except ValueError:
                cur = None
            if cur == CandidateState.APPLIED:
                rs = getattr(application, "resume_status", None) or "pending"
                if rs != "parsed":
                    raise InvalidTransitionError(
                        application.status,
                        action.value,
                        "Resume analysis must complete successfully before approving for interview.",
                    )

        # Precondition: To HIRE, the first level interview MUST be completed.
        if action == TransitionAction.HIRE:
            if not application.interview or not application.interview.first_level_completed:
                raise InvalidTransitionError(
                    application.status, action.value,
                    "Cannot hire candidate: First-level interview is not completed."
                )
        
        # Precondition: To CALL_FOR_INTERVIEW (Physical), the AI interview should be completed.
        if action == TransitionAction.CALL_FOR_INTERVIEW:
            if not application.interview or not application.interview.first_level_completed:
                # Require notes if bypassing AI interview
                if not notes:
                    raise InvalidTransitionError(
                        application.status, action.value,
                        "Bypassing AI interview requires providing justification in notes."
                    )
                logger.warning(f"HR bypassed AI interview for application {application.id}")
                
    def _resolve_approve_target(self, application: Application) -> CandidateState:
        """Determine target state for APPROVE based on job configuration."""
        job = application.job
        if not job:
            # Load the job if not eagerly loaded
            job = self.db.query(Job).filter(Job.id == application.job_id).first()

        if job and job.aptitude_enabled:
            return CandidateState.APTITUDE_ROUND
        return CandidateState.AI_INTERVIEW

    def _log_transition(
        self,
        application_id: int,
        from_state: str,
        to_state: str,
        action: str,
        user_id: Optional[int] = None,
        notes: Optional[str] = None,
    ):
        """Write an audit log for every state transition."""
        details = {
            "from_state": from_state,
            "to_state": to_state,
            "action": action,
        }
        if notes:
            details["notes"] = notes

        log = AuditLog(
            user_id=user_id,
            action="STATE_TRANSITION",
            resource_type="Application",
            resource_id=application_id,
            details=json.dumps(details),
        )
        self.db.add(log)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Transition Result DTO
# ─────────────────────────────────────────────────────────────────────────────

class TransitionResult:
    """Immutable result of a state transition."""

    __slots__ = ("application_id", "from_state", "to_state", "action", "email_type")

    def __init__(
        self,
        application_id: int,
        from_state: str,
        to_state: str,
        action: str,
        email_type: Optional[str],
    ):
        self.application_id = application_id
        self.from_state = from_state
        self.to_state = to_state
        self.action = action
        self.email_type = email_type

    def __repr__(self):
        return (
            f"TransitionResult(app={self.application_id}, "
            f"{self.from_state}->{self.to_state}, "
            f"action={self.action}, email={self.email_type})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. UI Button Mapping Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_ui_buttons_for_state(state: str) -> List[Dict[str, str]]:
    """
    Return the list of UI buttons that should be rendered for a given state.
    VIEW REPORT is always included.
    """
    buttons = []

    if state == CandidateState.APPLIED.value:
        buttons = [
            {"action": "approve_for_interview", "label": "Approve for Interview", "variant": "primary"},
            {"action": "reject", "label": "Reject", "variant": "destructive"},
        ]
    elif state == CandidateState.APTITUDE_ROUND.value:
        buttons = [
            {"action": "reject", "label": "Reject", "variant": "destructive"},
        ]
    elif state == CandidateState.AI_INTERVIEW.value:
        buttons = [
            {"action": "reject", "label": "Reject", "variant": "destructive"},
        ]
    elif state == CandidateState.AI_INTERVIEW_COMPLETED.value:
        buttons = [
            {"action": "call_for_interview", "label": "Call for Interview", "variant": "primary"},
            {"action": "review_later", "label": "Review Later", "variant": "secondary"},
            {"action": "reject", "label": "Reject", "variant": "destructive"},
        ]
    elif state == CandidateState.REVIEW_LATER.value:
        buttons = [
            {"action": "call_for_interview", "label": "Call for Interview", "variant": "primary"},
            {"action": "reject", "label": "Reject", "variant": "destructive"},
        ]
    elif state == CandidateState.PHYSICAL_INTERVIEW.value:
        buttons = [
            {"action": "hire", "label": "Hire", "variant": "success"},
            {"action": "reject", "label": "Reject", "variant": "destructive"},
        ]
    # hired and rejected: no action buttons

    # VIEW REPORT is always appended
    buttons.append({"action": "view_report", "label": "View Report", "variant": "outline"})

    return buttons
