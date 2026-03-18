"""Schema alignment cleanup — drop columns removed from ORM models

Revision ID: 002_schema_alignment_cleanup
Revises: 001_critical_fixes
Create Date: 2026-03-03

Changes:
- Drop deleted_at from: jobs, applications, resume_extractions, interviews, notifications
- Drop phase_number from: interview_questions

These columns were added in 001_critical_fixes but subsequently removed from
SQLAlchemy models during the Beta Integrity Enforcement pass.
This migration brings the live DB schema back in sync with models.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_schema_alignment_cleanup'
down_revision = '001_critical_fixes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Jobs: drop deleted_at ---
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index('ix_jobs_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- Applications: drop deleted_at ---
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_index('ix_applications_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- ResumeExtractions: drop deleted_at ---
    with op.batch_alter_table('resume_extractions', schema=None) as batch_op:
        batch_op.drop_index('ix_resume_extractions_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- Interviews: drop deleted_at ---
    with op.batch_alter_table('interviews', schema=None) as batch_op:
        batch_op.drop_index('ix_interviews_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- Notifications: drop deleted_at ---
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index('ix_notifications_deleted_at')
        batch_op.drop_column('deleted_at')

    # --- InterviewQuestions: drop phase_number ---
    with op.batch_alter_table('interview_questions', schema=None) as batch_op:
        batch_op.drop_index('ix_interview_questions_phase_number')
        batch_op.drop_column('phase_number')


def downgrade() -> None:
    """Recreate dropped columns for rollback safety."""

    # --- InterviewQuestions: restore phase_number ---
    with op.batch_alter_table('interview_questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phase_number', sa.Integer(), nullable=True))
        batch_op.create_index('ix_interview_questions_phase_number', ['phase_number'])

    # --- Notifications: restore deleted_at ---
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_notifications_deleted_at', ['deleted_at'])

    # --- Interviews: restore deleted_at ---
    with op.batch_alter_table('interviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_interviews_deleted_at', ['deleted_at'])

    # --- ResumeExtractions: restore deleted_at ---
    with op.batch_alter_table('resume_extractions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_resume_extractions_deleted_at', ['deleted_at'])

    # --- Applications: restore deleted_at ---
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_applications_deleted_at', ['deleted_at'])

    # --- Jobs: restore deleted_at ---
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_jobs_deleted_at', ['deleted_at'])
