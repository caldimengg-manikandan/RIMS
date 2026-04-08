-- RLS Hardening for Applications and Jobs (Phase 2)
-- Enables strict row level security and defines HR and Admin access policies.

-- 1. Applications Table
ALTER TABLE IF EXISTS applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS applications FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin Access All Apps" ON applications;
CREATE POLICY "Admin Access All Apps" ON applications FOR ALL USING (
  EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', true)::int AND role = 'super_admin')
);

DROP POLICY IF EXISTS "HR Ownership Access Apps" ON applications;
CREATE POLICY "HR Ownership Access Apps" ON applications FOR ALL USING (
  hr_id = current_setting('app.current_user_id', true)::int OR
  job_id IN (SELECT id FROM jobs WHERE hr_id = current_setting('app.current_user_id', true)::int)
);

-- 2. Jobs Table
ALTER TABLE IF EXISTS jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS jobs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin Access All Jobs" ON jobs;
CREATE POLICY "Admin Access All Jobs" ON jobs FOR ALL USING (
  EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', true)::int AND role = 'super_admin')
);

DROP POLICY IF EXISTS "HR Ownership Access Jobs" ON jobs;
CREATE POLICY "HR Ownership Access Jobs" ON jobs FOR ALL USING (
  hr_id = current_setting('app.current_user_id', true)::int
);

DROP POLICY IF EXISTS "Public View Open Jobs" ON jobs;
CREATE POLICY "Public View Open Jobs" ON jobs FOR SELECT USING (status = 'open');

-- 3. Audit Logs Visibility
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin Access All Audit" ON audit_logs;
CREATE POLICY "Admin Access All Audit" ON audit_logs FOR ALL USING (
  EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', true)::int AND role = 'super_admin')
);

DROP POLICY IF EXISTS "HR Ownership Audit" ON audit_logs;
CREATE POLICY "HR Ownership Audit" ON audit_logs FOR SELECT USING (
  user_id = current_setting('app.current_user_id', true)::int
);
