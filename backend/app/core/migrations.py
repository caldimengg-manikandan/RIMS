"""
Startup migration helper — safely adds missing columns to existing tables.
Works with MySQL.
Called from main.py AFTER Base.metadata.create_all().
"""
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine


# Each tuple: (table, column, column_type_sql)
_REQUIRED_COLUMNS = [
    ("jobs", "aptitude_questions_file", "VARCHAR(500)"),
    ("jobs", "job_id", "VARCHAR(50)"),
    ("interview_questions", "question_options", "TEXT"),
    ("interview_questions", "correct_option", "INTEGER"),
    ("resume_extractions", "summary", "TEXT"),
    ("resume_extractions", "resume_score", "FLOAT"),
    ("resume_extractions", "skill_match_percentage", "FLOAT"),
    ("jobs", "interview_token", "VARCHAR(50)"),
    ("interviews", "test_id", "VARCHAR(50)"),
    # Enterprise Pipeline Columns
    ("applications", "resume_score", "FLOAT"),
    ("applications", "aptitude_score", "FLOAT"),
    ("applications", "interview_score", "FLOAT"),
    ("applications", "composite_score", "FLOAT"),
    ("applications", "recommendation", "VARCHAR(50)"),
    # Report identification columns
    ("interview_reports", "application_id", "INTEGER"),
    ("interview_reports", "job_id", "INTEGER"),
    ("interview_reports", "termination_reason", "VARCHAR(255)"),
    ("jobs", "interview_token", "VARCHAR(50)"),
    ("interviews", "test_id", "VARCHAR(50)"),
    ("interviews", "video_recording_path", "VARCHAR(500)"),
]


def run_startup_migrations(engine: Engine):
    """Check for missing columns and add them safely."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, col_type in _REQUIRED_COLUMNS:
            if table not in inspector.get_table_names():
                continue  # table doesn't exist yet; create_all will handle it
            existing = [c["name"] for c in inspector.get_columns(table)]
            if column not in existing:
                # Use dialect-safe ALTER TABLE
                stmt = text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')
                conn.execute(stmt)
                print(f"✅ Migration: added column {table}.{column} ({col_type})")

    # Add unique constraints if missing (safe — errors caught individually)
    _REQUIRED_CONSTRAINTS = [
        ("applications", "uq_application_job_email",
         "CREATE UNIQUE INDEX IF NOT EXISTS uq_application_job_email ON applications(job_id, candidate_email)"),
        ("interview_answers", "uq_answer_per_question",
         "CREATE UNIQUE INDEX IF NOT EXISTS uq_answer_per_question ON interview_answers(question_id)"),
    ]
    with engine.begin() as conn:
        for table, constraint_name, create_sql in _REQUIRED_CONSTRAINTS:
            if table not in inspector.get_table_names():
                continue
            try:
                conn.execute(text(create_sql))
                print(f"✅ Migration: ensured constraint {constraint_name} on {table}")
            except Exception as e:
                # Constraint may already exist or table has duplicate data
                print(f"⚠️ Migration: skipped constraint {constraint_name}: {e}")
