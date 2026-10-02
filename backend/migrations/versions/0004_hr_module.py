"""HR module: leave (types/balances/requests) and minimal recruitment

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-03

Scope decisions (payroll stays out entirely, per the plan - this is leave + recruitment only):

- Leave is self-service for employees who have an account (supervisor/manager/plant_head/
  hr_admin/recruiter). `role='worker'` employees (added in 0002) are out of scope for leave
  specifically in this MVP, same reasoning as clock-in being kiosk-operated: there is no stable
  "which line/manager owns this worker" fact to hang an on-behalf-of flow off yet. Approval is
  hr_admin/plant_head only, plant-matched against the requesting employee.
- Recruitment (job_postings/candidates/applications) is globally scoped to the
  hr_admin/recruiter/plant_head roles, not plant-filtered - acceptable for this single-plant-per-
  demo MVP; multi-plant recruiting silos would be a real follow-up, not a bug.
- Candidate resumes go to a private Supabase Storage bucket (`candidate-resumes`), uploaded by
  the browser directly via a short-lived signed URL the backend issues with the service-role
  key - verified against the real local Storage API before writing app/routes/recruitment.py
  (POST .../storage/v1/object/upload/sign/{bucket}/{path} -> {url, token}), not assumed from
  memory. Postgres only ever stores the resulting object path.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OWN_EMPLOYEE = "employee_id = (SELECT employee_id FROM profiles WHERE id = auth.uid())"
_ADMIN_FOR_TARGET = """
    EXISTS (
        SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
        JOIN employees target ON target.id = {table}.employee_id
        WHERE p.id = auth.uid() AND (e.role = 'hr_admin' OR e.role = 'plant_head')
        AND e.plant_id = target.plant_id
    )
"""
_RECRUITING_ROLE = """
    EXISTS (
        SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
        WHERE p.id = auth.uid() AND e.role IN ('hr_admin', 'recruiter', 'plant_head')
    )
"""


def upgrade() -> None:
    op.execute("""
        CREATE TABLE leave_types (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            annual_quota_days INT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE leave_balances (
            employee_id BIGINT NOT NULL REFERENCES employees(id),
            leave_type_id BIGINT NOT NULL REFERENCES leave_types(id),
            year INT NOT NULL,
            remaining_days NUMERIC(4, 1) NOT NULL,
            PRIMARY KEY (employee_id, leave_type_id, year)
        )
    """)
    op.execute("""
        CREATE TABLE leave_requests (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            employee_id BIGINT NOT NULL REFERENCES employees(id),
            leave_type_id BIGINT NOT NULL REFERENCES leave_types(id),
            starts_on DATE NOT NULL,
            ends_on DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            approved_by BIGINT REFERENCES employees(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE job_postings (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            plant_id BIGINT NOT NULL REFERENCES plants(id),
            title TEXT NOT NULL,
            department_id BIGINT REFERENCES departments(id),
            status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
            created_by BIGINT NOT NULL REFERENCES employees(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE candidates (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            resume_storage_path TEXT
        )
    """)
    op.execute("""
        CREATE TABLE applications (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            job_posting_id BIGINT NOT NULL REFERENCES job_postings(id),
            candidate_id BIGINT NOT NULL REFERENCES candidates(id),
            stage TEXT NOT NULL DEFAULT 'applied'
                CHECK (stage IN ('applied', 'screening', 'interview', 'offer', 'rejected', 'hired')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    for table in ("leave_types", "leave_balances", "leave_requests", "job_postings", "candidates", "applications"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute("CREATE POLICY leave_types_select ON leave_types FOR SELECT TO authenticated USING (true)")
    op.execute("""
        CREATE POLICY leave_types_admin_write ON leave_types FOR INSERT TO authenticated WITH CHECK (
            EXISTS (SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                    WHERE p.id = auth.uid() AND e.role = 'hr_admin')
        )
    """)

    op.execute(f"CREATE POLICY leave_balances_select ON leave_balances FOR SELECT TO authenticated USING ({_OWN_EMPLOYEE} OR {_ADMIN_FOR_TARGET.format(table='leave_balances')})")
    op.execute(f"CREATE POLICY leave_balances_admin_write ON leave_balances FOR INSERT TO authenticated WITH CHECK ({_ADMIN_FOR_TARGET.format(table='leave_balances')})")
    op.execute(f"CREATE POLICY leave_balances_admin_update ON leave_balances FOR UPDATE TO authenticated USING ({_ADMIN_FOR_TARGET.format(table='leave_balances')})")

    op.execute(f"CREATE POLICY leave_requests_select ON leave_requests FOR SELECT TO authenticated USING ({_OWN_EMPLOYEE} OR {_ADMIN_FOR_TARGET.format(table='leave_requests')})")
    op.execute(f"CREATE POLICY leave_requests_self_insert ON leave_requests FOR INSERT TO authenticated WITH CHECK ({_OWN_EMPLOYEE})")
    op.execute(f"CREATE POLICY leave_requests_admin_update ON leave_requests FOR UPDATE TO authenticated USING ({_ADMIN_FOR_TARGET.format(table='leave_requests')})")

    for table in ("job_postings", "candidates", "applications"):
        op.execute(f"CREATE POLICY {table}_recruiting_select ON {table} FOR SELECT TO authenticated USING ({_RECRUITING_ROLE})")
        op.execute(f"CREATE POLICY {table}_recruiting_insert ON {table} FOR INSERT TO authenticated WITH CHECK ({_RECRUITING_ROLE})")
        op.execute(f"CREATE POLICY {table}_recruiting_update ON {table} FOR UPDATE TO authenticated USING ({_RECRUITING_ROLE})")

    op.execute("GRANT SELECT ON leave_types TO authenticated")
    op.execute("GRANT INSERT ON leave_types TO authenticated")
    op.execute("GRANT SELECT, INSERT, UPDATE ON leave_balances TO authenticated")
    op.execute("GRANT SELECT, INSERT, UPDATE ON leave_requests TO authenticated")
    op.execute("GRANT SELECT, INSERT, UPDATE ON job_postings, candidates, applications TO authenticated")
    op.execute(
        "GRANT ALL ON leave_types, leave_balances, leave_requests, job_postings, candidates, applications "
        "TO service_role"
    )


def downgrade() -> None:
    for table in ("applications", "candidates", "job_postings", "leave_requests", "leave_balances", "leave_types"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
