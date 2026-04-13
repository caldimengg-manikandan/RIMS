import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

SQL_MIGRATION = """
-- 0. FORCE ROLE COMPLIANCE
-- The app user (postgres) has BYPASSRLS=True by default in this environment, which overrides all policies.
-- We MUST revoke it to enable RLS protection.
ALTER ROLE postgres NOBYPASSRLS;

-- 1. CLEANUP JOB POLICIES
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public View Open Jobs" ON jobs;
DROP POLICY IF EXISTS "HR Ownership Access Jobs" ON jobs;
DROP POLICY IF EXISTS "Admin Access All Jobs" ON jobs;

-- Policy for Candidates (Anonymous/Public)
-- Only allows viewing 'open' jobs when NOT logged in as a staff member
CREATE POLICY "Public View Open Jobs" ON jobs 
FOR SELECT 
USING (
    status = 'open' 
    AND (NULLIF(current_setting('app.current_user_id', true), '') IS NULL)
);

-- Policy for HRs (Strict Ownership)
CREATE POLICY "HR Ownership Access Jobs" ON jobs 
FOR ALL 
USING (
    hr_id = (current_setting('app.current_user_id', true))::integer
);

-- Policy for Admins
CREATE POLICY "Admin Access All Jobs" ON jobs 
FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM users 
        WHERE id = (current_setting('app.current_user_id', true))::integer 
        AND role = 'super_admin'
    )
);

-- 2. CLEANUP APPLICATION POLICIES
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "HR Ownership Access Apps" ON applications;
DROP POLICY IF EXISTS "Admin Access All Apps" ON applications;
DROP POLICY IF EXISTS "HR Ownership Access" ON applications; -- Legacy
DROP POLICY IF EXISTS "Admin Access All" ON applications;     -- Legacy

-- HR Ownership: See apps you own or apps for jobs you own
CREATE POLICY "HR Ownership Access Apps" ON applications 
FOR ALL 
USING (
    hr_id = (current_setting('app.current_user_id', true))::integer
    OR 
    job_id IN (SELECT id FROM jobs WHERE hr_id = (current_setting('app.current_user_id', true))::integer)
);

-- Admin Access
CREATE POLICY "Admin Access All Apps" ON applications 
FOR ALL 
USING (
    EXISTS (
        SELECT 1 FROM users 
        WHERE id = (current_setting('app.current_user_id', true))::integer 
        AND role = 'super_admin'
    )
);

-- 3. INTERVIEWS ISOLATION
ALTER TABLE interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE interviews FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "HR Ownership Access Interviews" ON interviews;
DROP POLICY IF EXISTS "Admin Access All Interviews" ON interviews;

CREATE POLICY "HR Ownership Access Interviews" ON interviews 
FOR ALL 
USING (
    application_id IN (
        SELECT id FROM applications 
        WHERE hr_id = (current_setting('app.current_user_id', true))::integer
        OR job_id IN (SELECT id FROM jobs WHERE hr_id = (current_setting('app.current_user_id', true))::integer)
    )
);

CREATE POLICY "Admin Access All Interviews" ON interviews 
FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE id = (current_setting('app.current_user_id', true))::integer AND role = 'super_admin')
);

-- 4. HIRING DECISIONS ISOLATION
ALTER TABLE hiring_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hiring_decisions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "HR Ownership Access Decisions" ON hiring_decisions;
DROP POLICY IF EXISTS "Admin Access All Decisions" ON hiring_decisions;

CREATE POLICY "HR Ownership Access Decisions" ON hiring_decisions 
FOR ALL USING (
    application_id IN (
        SELECT id FROM applications 
        WHERE hr_id = (current_setting('app.current_user_id', true))::integer
        OR job_id IN (SELECT id FROM jobs WHERE hr_id = (current_setting('app.current_user_id', true))::integer)
    )
);

CREATE POLICY "Admin Access All Decisions" ON hiring_decisions 
FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE id = (current_setting('app.current_user_id', true))::integer AND role = 'super_admin')
);

-- 5. NOTIFICATIONS ISOLATION
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "User Own Notifications" ON notifications;
CREATE POLICY "User Own Notifications" ON notifications 
FOR ALL USING (
    user_id = (current_setting('app.current_user_id', true))::integer
);
"""

def run_rls_hardening():
    print("Executing RLS Hardening migration...")
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # We must use raw connection for multiple statements if using text() wrapper in some drivers
            # but Postgres/SQLAlchemy usually handles it. 
            # We split by ; to be safe.
            for statement in SQL_MIGRATION.split(';'):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
            trans.commit()
            print("RLS Hardening completed successfully!")
        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_rls_hardening()
