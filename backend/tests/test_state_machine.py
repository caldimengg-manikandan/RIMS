"""
test_state_machine.py
=====================
Unit tests for app.services.state_machine.CandidateStateMachine.

Strategy:
 - Uses MagicMock objects for Application and DB session (no SQLite).
 - Tests all valid transitions in the _TRANSITION_TABLE.
 - Tests InvalidTransitionError for disallowed transitions.
 - Tests terminal-state blocking.
 - Tests get_allowed_actions.
 - Tests _resolve_approve_target based on job.aptitude_enabled.
 - Tests validate_transition directly.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _mock_app(status: str, resume_status: str = "parsed", resume_score: float = 75.0,
              job_aptitude_enabled: bool = False, has_interview: bool = False,
              first_level_completed: bool = False) -> MagicMock:
    """Build a minimal mock Application object."""
    app = MagicMock()
    app.id = 1
    app.status = status
    app.resume_status = resume_status
    app.resume_score = resume_score
    app.candidate_email = "candidate@example.com"

    # Mock job
    job = MagicMock()
    job.aptitude_enabled = job_aptitude_enabled
    app.job = job
    app.job_id = 99

    # Mock interview
    if has_interview:
        interview = MagicMock()
        interview.id = 1
        interview.first_level_completed = first_level_completed
        app.interview = interview
    else:
        app.interview = None

    return app


def _mock_db(app_obj=None) -> MagicMock:
    """Build a minimal mock DB session."""
    db = MagicMock()
    # query(...).with_for_update().filter(...).first() returns app_obj
    db.query.return_value.with_for_update.return_value.filter.return_value.first.return_value = app_obj
    db.execute.return_value = None
    return db


def _make_fsm(db=None):
    from app.services.state_machine import CandidateStateMachine
    db = db or MagicMock()
    return CandidateStateMachine(db)


# ══════════════════════════════════════════════════════════════════════════════
# 1. validate_transition — happy paths
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateTransition:
    """Tests for the pure validate_transition logic (no DB or audit logging)."""

    def test_applied_to_screened_via_system_parsing_complete(self):
        from app.services.state_machine import CandidateStateMachine
        from app.domain.constants import CandidateState, TransitionAction

        fsm = _make_fsm()
        app = _mock_app("applied")
        result = fsm.validate_transition(app, TransitionAction.SYSTEM_PARSING_COMPLETE)
        assert result == CandidateState.SCREENED

    def test_applied_reject(self):
        from app.services.state_machine import CandidateStateMachine
        from app.domain.constants import CandidateState, TransitionAction

        fsm = _make_fsm()
        app = _mock_app("applied")
        result = fsm.validate_transition(app, TransitionAction.REJECT)
        assert result == CandidateState.REJECTED

    def test_screened_reject(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("screened")
        result = fsm.validate_transition(app, TransitionAction.REJECT)
        assert result == CandidateState.REJECTED

    def test_interview_completed_to_hired(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("interview_completed")
        result = fsm.validate_transition(app, TransitionAction.HIRE)
        assert result == CandidateState.HIRED

    def test_interview_completed_to_review_later(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("interview_completed")
        result = fsm.validate_transition(app, TransitionAction.REVIEW_LATER)
        assert result == CandidateState.REVIEW_LATER

    def test_hired_to_offer_sent(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("hired")
        result = fsm.validate_transition(app, TransitionAction.SEND_OFFER)
        assert result == CandidateState.OFFER_SENT

    def test_offer_sent_to_accepted(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("offer_sent")
        result = fsm.validate_transition(app, TransitionAction.ACCEPT_OFFER)
        assert result == CandidateState.ACCEPTED

    def test_accepted_to_onboarded(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("accepted")
        result = fsm.validate_transition(app, TransitionAction.SYSTEM_ONBOARD)
        assert result == CandidateState.ONBOARDED

    def test_aptitude_round_to_ai_interview(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("aptitude_round")
        result = fsm.validate_transition(app, TransitionAction.SYSTEM_APTITUDE_COMPLETE)
        assert result == CandidateState.AI_INTERVIEW

    def test_physical_interview_to_hired(self):
        from app.domain.constants import CandidateState, TransitionAction
        fsm = _make_fsm()
        app = _mock_app("physical_interview")
        result = fsm.validate_transition(app, TransitionAction.HIRE)
        assert result == CandidateState.HIRED


# ══════════════════════════════════════════════════════════════════════════════
# 2. validate_transition — error cases
# ══════════════════════════════════════════════════════════════════════════════

class TestInvalidTransitions:

    def test_invalid_transition_raises_error(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("applied")
        with pytest.raises(InvalidTransitionError):
            # Cannot HIRE from applied
            fsm.validate_transition(app, TransitionAction.HIRE)

    def test_terminal_state_onboarded_blocks_all(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("onboarded")
        with pytest.raises(InvalidTransitionError) as exc_info:
            fsm.validate_transition(app, TransitionAction.REJECT)
        assert "terminal" in str(exc_info.value).lower()

    def test_terminal_state_rejected_blocks_all(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("rejected")
        with pytest.raises(InvalidTransitionError):
            fsm.validate_transition(app, TransitionAction.HIRE)

    def test_unknown_state_raises_invalid_transition(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("GHOST_STATE")
        with pytest.raises(InvalidTransitionError):
            fsm.validate_transition(app, TransitionAction.REJECT)

    def test_offer_sent_to_hired_is_invalid(self):
        """Cannot jump directly from offer_sent to hired."""
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("offer_sent")
        with pytest.raises(InvalidTransitionError):
            fsm.validate_transition(app, TransitionAction.HIRE)

    def test_screened_to_onboarded_is_invalid(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("screened")
        with pytest.raises(InvalidTransitionError):
            fsm.validate_transition(app, TransitionAction.SYSTEM_ONBOARD)


# ══════════════════════════════════════════════════════════════════════════════
# 3. _resolve_approve_target
# ══════════════════════════════════════════════════════════════════════════════

class TestResolveApproveTarget:

    def test_approve_without_aptitude_goes_to_ai_interview(self):
        from app.domain.constants import CandidateState
        fsm = _make_fsm()
        app = _mock_app("screened", job_aptitude_enabled=False)
        target = fsm._resolve_approve_target(app)
        assert target == CandidateState.AI_INTERVIEW

    def test_approve_with_aptitude_goes_to_aptitude_round(self):
        from app.domain.constants import CandidateState
        fsm = _make_fsm()
        app = _mock_app("screened", job_aptitude_enabled=True)
        target = fsm._resolve_approve_target(app)
        assert target == CandidateState.APTITUDE_ROUND

    def test_approve_with_no_job_defaults_to_ai_interview(self):
        """If job is not loaded, should default to AI_INTERVIEW."""
        from app.domain.constants import CandidateState
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        fsm = _make_fsm(db)
        app = _mock_app("screened")
        app.job = None  # Force job not loaded
        target = fsm._resolve_approve_target(app)
        assert target == CandidateState.AI_INTERVIEW


# ══════════════════════════════════════════════════════════════════════════════
# 4. get_allowed_actions
# ══════════════════════════════════════════════════════════════════════════════

class TestGetAllowedActions:

    def test_applied_has_expected_actions(self):
        fsm = _make_fsm()
        app = _mock_app("applied")
        actions = fsm.get_allowed_actions(app)
        assert "reject" in actions
        # SYSTEM actions should be excluded
        assert "system_parsing_complete" not in actions

    def test_interview_completed_has_hire_and_reject(self):
        fsm = _make_fsm()
        app = _mock_app("interview_completed")
        actions = fsm.get_allowed_actions(app)
        assert "hire" in actions
        assert "reject" in actions

    def test_terminal_state_has_no_actions(self):
        fsm = _make_fsm()
        app = _mock_app("onboarded")
        actions = fsm.get_allowed_actions(app)
        assert actions == []

    def test_rejected_has_no_actions(self):
        fsm = _make_fsm()
        app = _mock_app("rejected")
        actions = fsm.get_allowed_actions(app)
        assert actions == []

    def test_unknown_state_returns_empty(self):
        fsm = _make_fsm()
        app = _mock_app("INVALID_STATUS")
        actions = fsm.get_allowed_actions(app)
        assert actions == []


# ══════════════════════════════════════════════════════════════════════════════
# 5. _check_preconditions
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckPreconditions:

    def test_approve_from_applied_requires_resume_parsed(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        # Resume not parsed, no score
        app = _mock_app("applied", resume_status="pending", resume_score=0.0)
        with pytest.raises(InvalidTransitionError) as exc_info:
            fsm._check_preconditions(app, TransitionAction.APPROVE_FOR_INTERVIEW)
        assert "resume" in str(exc_info.value).lower()

    def test_approve_from_applied_with_parsed_status_passes(self):
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("applied", resume_status="parsed", resume_score=60.0)
        # Should NOT raise
        fsm._check_preconditions(app, TransitionAction.APPROVE_FOR_INTERVIEW)

    def test_hire_without_completed_interview_raises(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("interview_completed", has_interview=True, first_level_completed=False)
        with pytest.raises(InvalidTransitionError) as exc_info:
            fsm._check_preconditions(app, TransitionAction.HIRE)
        assert "first-level" in str(exc_info.value).lower()

    def test_hire_with_completed_interview_passes(self):
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("interview_completed", has_interview=True, first_level_completed=True)
        # Should NOT raise
        fsm._check_preconditions(app, TransitionAction.HIRE)

    def test_call_for_interview_without_notes_and_incomplete_interview_raises(self):
        from app.services.state_machine import InvalidTransitionError
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("interview_completed", has_interview=True, first_level_completed=False)
        with pytest.raises(InvalidTransitionError):
            fsm._check_preconditions(app, TransitionAction.CALL_FOR_INTERVIEW, notes=None)

    def test_call_for_interview_with_notes_and_incomplete_interview_passes(self):
        """Providing notes allows bypassing AI interview requirement."""
        from app.domain.constants import TransitionAction
        fsm = _make_fsm()
        app = _mock_app("interview_completed", has_interview=True, first_level_completed=False)
        # Should NOT raise when notes provided
        fsm._check_preconditions(app, TransitionAction.CALL_FOR_INTERVIEW, notes="Bypassing AI due to technical issue")


# ══════════════════════════════════════════════════════════════════════════════
# 6. TransitionResult
# ══════════════════════════════════════════════════════════════════════════════

class TestTransitionResult:

    def test_repr_contains_key_info(self):
        from app.services.state_machine import TransitionResult
        r = TransitionResult(
            application_id=5,
            from_state="applied",
            to_state="screened",
            action="system_parsing_complete",
            email_type=None,
        )
        s = repr(r)
        assert "5" in s
        assert "applied" in s
        assert "screened" in s

    def test_slots_accessible(self):
        from app.services.state_machine import TransitionResult
        r = TransitionResult(1, "applied", "screened", "mark_screened", "approved_for_interview")
        assert r.email_type == "approved_for_interview"
        assert r.action == "mark_screened"


# ══════════════════════════════════════════════════════════════════════════════
# 7. get_ui_buttons_for_state
# ══════════════════════════════════════════════════════════════════════════════

class TestGetUIButtonsForState:

    def test_applied_state_has_reject_button(self):
        from app.services.state_machine import get_ui_buttons_for_state
        buttons = get_ui_buttons_for_state("applied")
        actions = [b["action"] for b in buttons]
        assert "reject" in actions

    def test_interview_completed_has_hire_button(self):
        from app.services.state_machine import get_ui_buttons_for_state
        buttons = get_ui_buttons_for_state("interview_completed")
        actions = [b["action"] for b in buttons]
        assert "hire" in actions

    def test_every_state_has_view_report_button(self):
        """All states should include the view_report button."""
        from app.services.state_machine import get_ui_buttons_for_state
        for state in ["applied", "screened", "interview_completed", "hired", "onboarded"]:
            buttons = get_ui_buttons_for_state(state)
            actions = [b["action"] for b in buttons]
            assert "view_report" in actions, f"view_report missing for state={state}"

    def test_hired_state_has_send_for_approval(self):
        from app.services.state_machine import get_ui_buttons_for_state
        buttons = get_ui_buttons_for_state("hired")
        actions = [b["action"] for b in buttons]
        assert "send_for_approval" in actions

    def test_buttons_have_required_keys(self):
        from app.services.state_machine import get_ui_buttons_for_state
        buttons = get_ui_buttons_for_state("interview_completed")
        for btn in buttons:
            assert "action" in btn
            assert "label" in btn
            assert "variant" in btn


# ══════════════════════════════════════════════════════════════════════════════
# 8. Constants
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:

    def test_candidate_state_values(self):
        from app.domain.constants import CandidateState
        assert CandidateState.APPLIED.value == "applied"
        assert CandidateState.ONBOARDED.value == "onboarded"

    def test_transition_action_values(self):
        from app.domain.constants import TransitionAction
        assert TransitionAction.HIRE.value == "hire"
        assert TransitionAction.REJECT.value == "reject"

    def test_terminal_states_immutable(self):
        from app.services.state_machine import TERMINAL_STATES
        from app.domain.constants import CandidateState
        assert CandidateState.ONBOARDED in TERMINAL_STATES
        assert CandidateState.REJECTED in TERMINAL_STATES
        assert CandidateState.HIRED not in TERMINAL_STATES
