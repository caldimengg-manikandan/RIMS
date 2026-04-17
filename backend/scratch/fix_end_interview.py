"""
Patches the /end interview endpoint to:
1. Make report generation run in background (no more blocking 20-60s wait)
2. Set hr_notes when candidate ends early
3. Accept ended_early flag from frontend
"""
import re

path = r'c:\Users\aashi\OneDrive\Desktop\Project\rims\backend\app\api\interviews.py'
with open(path, 'r', encoding='utf-8') as f:
    raw = f.read()

# Normalize to LF for robust matching
content = raw.replace('\r\n', '\n')

# ── Find the exact start/end markers ──────────────────────────────────────────
START_MARKER = '@router.post("/{interview_id}/end")\nasync def end_interview('
END_MARKER = '@router.post("/{interview_id}/abandon")'

start_idx = content.find(START_MARKER)
end_idx   = content.find(END_MARKER)

if start_idx == -1:
    print("ERROR: Could not find start marker")
    exit(1)
if end_idx == -1:
    print("ERROR: Could not find end marker")
    exit(1)

old_block = content[start_idx:end_idx]
print(f"Found block from char {start_idx} to {end_idx} ({len(old_block)} chars)")

# ── Replacement block ─────────────────────────────────────────────────────────
new_block = '''\
@router.post("/{interview_id}/end")
async def end_interview(
    request: Request,
    interview_id: int,
    background_tasks: BackgroundTasks,
    data: dict = Body(None),
    interview_session: Interview = Depends(get_current_interview),
    db: Session = Depends(get_db)
):
    """End interview manually (standard path).

    Returns immediately - AI report generation runs in a background task.
    """
    if interview_session.id != interview_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    request_id_header = request.headers.get("X-Request-ID")
    if settings.enable_request_id_idempotency and is_duplicate_request(
        request_id=request_id_header,
        scope="interviews.end",
        key=str(interview_id),
        ttl_seconds=120,
    ):
        interview_dup = db.query(Interview).filter(Interview.id == interview_id).first()
        if interview_dup and interview_dup.status != "in_progress":
            return {
                "success": True,
                "message": f"Interview is already in {interview_dup.status} state.",
                "status": interview_dup.status,
                "interview_id": interview_id,
                "interview_score": interview_dup.overall_score,
                "combined_score": interview_dup.overall_score,
            }

    interview = (
        db.query(Interview)
        .filter(Interview.id == interview_id)
        .with_for_update()
        .first()
    )

    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if interview.status != "in_progress":
        return {
            "success": True,
            "message": f"Interview is already in {interview.status} state.",
            "status": interview.status,
            "interview_id": interview_id,
            "interview_score": interview.overall_score,
            "combined_score": interview.overall_score,
        }

    # 1. Enforcement Check (Ensure sufficient answers if not already terminated or forced)
    is_forced = isinstance(data, dict) and data.get("force") is True
    ended_early = isinstance(data, dict) and data.get("ended_early") is True
    if interview.status != "terminated" and not is_forced:
        questions = db.query(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.question_type != "aptitude"
        ).all()
        question_ids = [q.id for q in questions]
        # Count answers by joining through question_id to avoid NULL interview_id issues
        answered_count = db.query(InterviewAnswer).filter(
            InterviewAnswer.question_id.in_(question_ids)
        ).count() if question_ids else 0

        if answered_count < len(questions) and len(questions) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Please answer all questions before ending. Missing: {len(questions) - answered_count}"
            )

    # 1.5 Handle termination reason if provided (proctoring violations etc.)
    if data and data.get("termination_reason"):
        from app.domain.models import InterviewIssue
        reason = data["termination_reason"]
        logger.warning(f"Manual termination requested for interview {interview_id}: {reason}")
        _set_interview_status(interview, "terminated")
        issue = InterviewIssue(
            interview_id=interview_id,
            candidate_name=interview.application.candidate_name if interview.application else "Candidate",
            candidate_email=interview.application.candidate_email if interview.application else "Email N/A",
            issue_type="proctoring",
            description=reason,
            status="resolved"
        )
        db.add(issue)
        db.commit()

    # 1.6 Annotate hr_notes when the candidate deliberately ends the interview early
    if (ended_early or is_forced) and interview.application:
        from datetime import datetime, timezone
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        early_note = (
            f"[{now_str}] Candidate ended the interview early using the 'End Early' button "
            "before completing all questions."
        )
        existing_notes = interview.application.hr_notes or ""
        interview.application.hr_notes = (
            (existing_notes.rstrip() + "\\n" + early_note).strip()
            if existing_notes
            else early_note
        )
        db.commit()

    # 2. Mark state immediately so the frontend sees a finished interview right away.
    interview.interview_stage = STAGE_COMPLETED
    if not interview.ended_at:
        interview.ended_at = datetime.now(timezone.utc)
    db.commit()

    # 3. Run the heavy AI report generation in the background so this response
    #    returns in milliseconds instead of blocking for 20-60 seconds.
    background_tasks.add_task(_finalize_interview_and_report, interview_id)
    logger.info(f"Interview {interview_id} ended — report generation queued as background task.")

    return {
        "success": True,
        "interview_id": interview_id,
        "status": interview.status,
        "interview_score": interview.overall_score,
        "combined_score": interview.overall_score,
    }

'''

new_content = content[:start_idx] + new_block + content[end_idx:]

# Restore original line endings
new_content_crlf = new_content.replace('\n', '\r\n')

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content_crlf)

print("SUCCESS: File patched!")
print(f"New file size: {len(new_content_crlf)} bytes")
