"""
Startup migration helper - safely adds missing columns to existing tables.
Works with both SQLite and PostgreSQL.
Called from main.py AFTER Base.metadata.create_all().
"""
import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


_REQUIRED_COLUMNS = [
    ("jobs", "aptitude_questions_file", "VARCHAR(500)"),
    ("jobs", "job_id", "VARCHAR(50)"),
    ("interview_questions", "question_options", "TEXT"),
    ("interview_questions", "correct_option", "INTEGER"),
    ("resume_extractions", "summary", "TEXT"),
    ("jobs", "interview_token", "VARCHAR(50)"),
    ("interviews", "test_id", "VARCHAR(50)"),
    # Resume parsing lifecycle tracking (HR gating + retry UI)
    ("applications", "resume_status", "VARCHAR(32) DEFAULT 'pending'"),
    ("applications", "resume_score", "FLOAT"),
    ("applications", "aptitude_score", "FLOAT"),
    ("applications", "interview_score", "FLOAT"),
    ("applications", "composite_score", "FLOAT"),
    ("applications", "recommendation", "VARCHAR(50)"),
    # Resume parsing persistence fields (may be missing on legacy DBs)
    ("applications", "candidate_phone_raw", "TEXT"),
    ("applications", "resume_file_name", "VARCHAR(255)"),
    ("applications", "candidate_photo_path", "TEXT"),
    ("applications", "hr_notes", "TEXT"),
    ("applications", "hr_id", "INTEGER REFERENCES users(id)"),
    ("interview_answers", "ai_used", "BOOLEAN DEFAULT FALSE"),
    ("interview_answers", "fallback_used", "BOOLEAN DEFAULT FALSE"),
    ("interview_answers", "confidence_score", "FLOAT"),
    ("interview_reports", "ai_used", "BOOLEAN DEFAULT FALSE"),
    ("interview_reports", "fallback_used", "BOOLEAN DEFAULT FALSE"),
    ("interview_reports", "confidence_score", "FLOAT"),
]


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table (PostgreSQL/SQLite compatible)."""
    # Use inspector for broad compatibility
    from sqlalchemy import inspect
    inspector = inspect(conn)
    if table_name not in inspector.get_table_names():
        return False
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def update_role_constraint(conn):
    """Safely update the role constraint to include 'pending_hr' and 'super_admin'."""
    try:
        # Check if we are on PostgreSQL
        if "postgresql" in str(conn.engine.url):
            conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_users_role"))
            conn.execute(text("""
                ALTER TABLE users ADD CONSTRAINT check_users_role 
                CHECK (role IN ('super_admin', 'hr', 'recruiter', 'pending_hr', 'candidate'))
            """))
            logger.info("Migration completed: updated check_users_role constraint")
        else:
            logger.info("Skipping constraint update: not on PostgreSQL")
    except Exception as exc:
        logger.warning(f"Migration failed to update role constraint: {exc}")


def run_startup_migrations(engine: Engine):
    """Check for missing columns and add them safely using PostgreSQL-friendly DDL."""
    inspector = inspect(engine)

    # 1. Ensure columns exist first
    with engine.connect() as conn:
        for table, column, col_type in _REQUIRED_COLUMNS:
            if table not in inspector.get_table_names():
                continue
            try:
                # PostgreSQL-native 'IF NOT EXISTS' for columns requires PG 9.6+, which we assume.
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"))
                conn.commit()
            except Exception as e:
                logger.warning(f"Failed to add column {table}.{column}: {e}")

        # Ensure approval_status exists on users (crucial for HR flow)
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'pending'"))
            conn.commit()
            logger.info("Ensured users.approval_status exists")
        except Exception as e:
            logger.warning(f"Failed to add users.approval_status: {e}")

        # Backfill resume_status from existing resume_extractions (metadata sync)
        try:
            if (
                column_exists(conn, "applications", "resume_status")
                and "resume_extractions" in inspector.get_table_names()
            ):
                conn.execute(text("""
                    UPDATE applications
                    SET resume_status = 'parsed'
                    WHERE (resume_status = 'pending' OR resume_status IS NULL)
                      AND EXISTS (
                        SELECT 1
                        FROM resume_extractions re
                        WHERE re.application_id = applications.id
                      )
                """))
                conn.commit()
                logger.info("Backfilled applications.resume_status from resume_extractions")
        except Exception as e:
            logger.warning(f"Failed to backfill applications.resume_status: {e}")

    # 2. Update Role Constraints
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS check_users_role"))
            conn.execute(text("""
                ALTER TABLE users ADD CONSTRAINT check_users_role 
                CHECK (role IN ('super_admin', 'hr', 'recruiter', 'pending_hr', 'candidate'))
            """))
            conn.commit()
            logger.info("Updated check_users_role constraint")
        except Exception as exc:
            logger.warning(f"Error updating role constraint: {exc}")

    # 3. Data normalization and Super Admin promotion
    with engine.connect() as conn:
        if column_exists(conn, "users", "approval_status"):
            try:
                # Normalize legacy roles
                conn.execute(text("""
                    UPDATE users
                    SET role = CASE
                        WHEN role IN ('admin', 'hr_manager', 'recruiter') AND approval_status = 'approved' THEN 'hr'
                        WHEN role IN ('admin', 'hr_manager', 'recruiter', 'hr') AND approval_status != 'approved' THEN 'pending_hr'
                        ELSE role
                    END
                    WHERE role NOT IN ('super_admin', 'candidate')
                """))
                
                # Promote specific user to super_admin
                conn.execute(text("""
                    UPDATE users 
                    SET role = 'super_admin', approval_status = 'approved'
                    WHERE email = 'caldiminternship@gmail.com'
                """))
                
                # Ensure existing staff are approved
                conn.execute(text("""
                    UPDATE users 
                    SET approval_status = 'approved' 
                    WHERE role IN ('super_admin', 'hr') AND approval_status IS NULL
                """))
                
                conn.commit()
                logger.info("Migration completed: normalized roles and promoted super admin")
            except Exception as exc:
                logger.warning(f"Migration failed to normalize roles: {exc}")
        
        # Populate Application.hr_id
        try:
            if column_exists(conn, "applications", "hr_id") and column_exists(conn, "jobs", "hr_id"):
                conn.execute(text("""
                    UPDATE applications
                    SET hr_id = (SELECT hr_id FROM jobs WHERE jobs.id = applications.job_id)
                    WHERE hr_id IS NULL
                """))
                conn.commit()
                logger.info("Migration completed: populated Application.hr_id")
        except Exception as exc:
            logger.warning(f"Migration failed to populate hr_id: {exc}")

    # 4. Constraints/Indexes
    required_constraints = [
        (
            "applications",
            "uq_application_job_email",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_application_job_email ON applications(job_id, candidate_email)",
        ),
        (
            "interview_answers",
            "uq_answer_per_question",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_answer_per_question ON interview_answers(question_id)",
        ),
    ]

    with engine.connect() as conn:
        for table, constraint_name, create_sql in required_constraints:
            if table not in inspector.get_table_names():
                continue
            try:
                conn.execute(text(create_sql))
                conn.commit()
                logger.info(f"Migration completed: ensured index {constraint_name}")
            except Exception as exc:
                logger.warning(f"Migration skipped index {constraint_name}: {exc}")
