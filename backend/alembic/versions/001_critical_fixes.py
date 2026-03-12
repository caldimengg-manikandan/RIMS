"""Critical database fixes - additive only

Revision ID: 001_critical_fixes
Revises: 
Create Date: 2026-03-02

Changes:
- Add otp_expiry to users
- Add deleted_at soft-delete columns to jobs, applications, resume_extractions, interviews, notifications
- Add phase_number to interview_questions
- Add interview_id FK, technical_score, completeness_score, clarity_score, depth_score, practicality_score to interview_answers
- Add composite index ix_applications_job_status on applications(job_id, status)
- Backfill interview_answers.interview_id from interview_questions
- Add check constraints on users.role, jobs.status, applications.status, hiring_decisions.decision

All changes are additive - no existing columns removed or renamed.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_critical_fixes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Users: add otp_expiry ---
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('otp_expiry', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_users_otp_expiry', ['otp_expiry'])
        batch_op.create_check_constraint('check_users_role', "role IN ('hr', 'admin')")

    # --- Jobs: add deleted_at + check constraint ---
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_jobs_deleted_at', ['deleted_at'])
        batch_op.create_check_constraint('check_jobs_status', "status IN ('open', 'closed', 'on_hold')")

    # --- Applications: add deleted_at + composite index + check constraint ---
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_applications_deleted_at', ['deleted_at'])
        batch_op.create_index('ix_applications_job_status', ['job_id', 'status'])
        batch_op.create_check_constraint(
            'check_applications_status',
            "status IN ('submitted', 'rejected', 'approved_for_interview', "
            "'interview_completed', 'hired', 'rejected_post_interview')"
        )

    # --- ResumeExtractions: add deleted_at ---
    with op.batch_alter_table('resume_extractions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_resume_extractions_deleted_at', ['deleted_at'])

    # --- Interviews: add deleted_at ---
    with op.batch_alter_table('interviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_interviews_deleted_at', ['deleted_at'])

    # --- InterviewQuestions: add phase_number ---
    with op.batch_alter_table('interview_questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phase_number', sa.Integer(), nullable=True))
        batch_op.create_index('ix_interview_questions_phase_number', ['phase_number'])

    # --- InterviewAnswers: add interview_id FK + 5 granular scores ---
    with op.batch_alter_table('interview_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('interview_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('technical_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('completeness_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('clarity_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('depth_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('practicality_score', sa.Float(), nullable=True))
        batch_op.create_index('ix_interview_answers_interview_id', ['interview_id'])
        batch_op.create_foreign_key(
            'fk_interview_answers_interview_id',
            'interviews',
            ['interview_id'], ['id'],
            ondelete='CASCADE'
        )

    # --- Notifications: add deleted_at ---
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_notifications_deleted_at', ['deleted_at'])

    # --- HiringDecisions: add check constraint ---
    with op.batch_alter_table('hiring_decisions', schema=None) as batch_op:
        batch_op.create_check_constraint('check_hiring_decision', "decision IN ('hired', 'rejected')")

    # --- Backfill interview_answers.interview_id from interview_questions ---
    op.execute(
        "UPDATE interview_answers SET interview_id = ("
        "SELECT interview_id FROM interview_questions "
        "WHERE interview_questions.id = interview_answers.question_id"
        ")"
    )


def downgrade() -> None:
    """Reverse all additive changes. Drop ONLY newly added columns/constraints."""

    # --- HiringDecisions: drop check constraint ---
    with op.batch_alter_table('hiring_decisions', schema=None) as batch_op:
        batch_op.drop_constraint('check_hiring_decision', type_='check')

    # --- Notifications: drop deleted_at ---
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index('ix_notifications_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- InterviewAnswers: drop new columns ---
    with op.batch_alter_table('interview_answers', schema=None) as batch_op:
        batch_op.drop_constraint('fk_interview_answers_interview_id', type_='foreignkey')
        batch_op.drop_index('ix_interview_answers_interview_id')
        batch_op.drop_column('practicality_score')
        batch_op.drop_column('depth_score')
        batch_op.drop_column('clarity_score')
        batch_op.drop_column('completeness_score')
        batch_op.drop_column('technical_score')
        batch_op.drop_column('interview_id')

    # --- InterviewQuestions: drop phase_number ---
    with op.batch_alter_table('interview_questions', schema=None) as batch_op:
        batch_op.drop_index('ix_interview_questions_phase_number')
        batch_op.drop_column('phase_number')

    # --- Interviews: drop deleted_at ---
    with op.batch_alter_table('interviews', schema=None) as batch_op:
        batch_op.drop_index('ix_interviews_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- ResumeExtractions: drop deleted_at ---
    with op.batch_alter_table('resume_extractions', schema=None) as batch_op:
        batch_op.drop_index('ix_resume_extractions_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- Applications: drop deleted_at + composite index + check constraint ---
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_constraint('check_applications_status', type_='check')
        batch_op.drop_index('ix_applications_job_status')
        batch_op.drop_index('ix_applications_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- Jobs: drop deleted_at + check constraint ---
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_constraint('check_jobs_status', type_='check')
        batch_op.drop_index('ix_jobs_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- Users: drop otp_expiry + check constraint ---
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('check_users_role', type_='check')
        batch_op.drop_index('ix_users_otp_expiry')
        batch_op.drop_column('otp_expiry')
