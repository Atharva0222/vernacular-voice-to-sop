"""employee module: departments, employee directory fields, worker role

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03

Adds the Employee management module. Two notable decisions:

1. `employees.role` gains a `worker` value. Every other role on this table is a privileged,
   login-capable staff role; `worker` is deliberately different - a worker-role row is a
   directory/scheduling record only and must never get a `profiles` row (no Supabase Auth
   account, ever). This is additive, not a reversal of the voice-to-SOP anonymity guarantee:
   the `reports` table still has zero FK to any employee, worker or otherwise - a worker filing
   a report is still fully anonymous. What changes is that a worker can now be *named* for
   Workforce-module scheduling/attendance (shift_assignments, attendance - see migration 0003),
   via the supervisor-operated kiosk pattern, not via the worker's own account.
2. `employees_scoped_select` (0001) only exposed a caller's own row plus same-plant plant_heads
   - too narrow for a directory. Replaced with a plant-wide SELECT policy reusing the
   `current_employee_plant_id()` SECURITY DEFINER helper already added in 0001 (same recursion
   fix applies here: anything in an `employees` policy that needs the caller's own plant_id must
   go through that function, not a direct subquery on `employees`).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE employees DROP CONSTRAINT employees_role_check")
    op.execute(
        "ALTER TABLE employees ADD CONSTRAINT employees_role_check "
        "CHECK (role IN ('worker', 'supervisor', 'manager', 'plant_head', 'hr_admin', 'recruiter'))"
    )

    op.execute("""
        CREATE TABLE departments (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            plant_id BIGINT NOT NULL REFERENCES plants(id),
            name TEXT NOT NULL,
            head_employee_id BIGINT REFERENCES employees(id)
        )
    """)

    op.execute("ALTER TABLE employees ADD COLUMN employee_code TEXT UNIQUE")
    op.execute("ALTER TABLE employees ADD COLUMN department_id BIGINT REFERENCES departments(id)")
    op.execute("ALTER TABLE employees ADD COLUMN job_title TEXT")
    # Org-chart reporting line. Deliberately not called "line"/"reporting_line" - `lines` already
    # means *production line* in this schema; see CLAUDE.md.
    op.execute("ALTER TABLE employees ADD COLUMN direct_manager_id BIGINT REFERENCES employees(id)")
    op.execute(
        "ALTER TABLE employees ADD COLUMN employment_status TEXT NOT NULL DEFAULT 'active' "
        "CHECK (employment_status IN ('active', 'on_leave', 'terminated'))"
    )
    op.execute("ALTER TABLE employees ADD COLUMN hire_date DATE")

    op.execute("ALTER TABLE departments ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY departments_select_all ON departments FOR SELECT TO authenticated USING (true)")
    op.execute("""
        CREATE POLICY departments_admin_write ON departments FOR INSERT TO authenticated WITH CHECK (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                WHERE p.id = auth.uid() AND (e.role = 'hr_admin' OR e.role = 'plant_head')
                AND e.plant_id = departments.plant_id
            )
        )
    """)
    op.execute("GRANT SELECT, INSERT ON departments TO authenticated")
    op.execute("GRANT ALL ON departments TO service_role")

    op.execute("DROP POLICY employees_scoped_select ON employees")
    op.execute(
        "CREATE POLICY employees_plant_select ON employees FOR SELECT TO authenticated "
        "USING (plant_id = public.current_employee_plant_id())"
    )
    op.execute("""
        CREATE POLICY employees_admin_insert ON employees FOR INSERT TO authenticated WITH CHECK (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                WHERE p.id = auth.uid() AND (e.role = 'hr_admin' OR e.role = 'plant_head')
                AND e.plant_id = employees.plant_id
            )
        )
    """)
    op.execute("""
        CREATE POLICY employees_admin_update ON employees FOR UPDATE TO authenticated USING (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                WHERE p.id = auth.uid() AND (e.role = 'hr_admin' OR e.role = 'plant_head')
                AND e.plant_id = employees.plant_id
            )
        )
    """)
    op.execute("GRANT INSERT, UPDATE ON employees TO authenticated")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS employees_admin_update ON employees")
    op.execute("DROP POLICY IF EXISTS employees_admin_insert ON employees")
    op.execute("DROP POLICY IF EXISTS employees_plant_select ON employees")
    op.execute(
        "CREATE POLICY employees_scoped_select ON employees FOR SELECT TO authenticated USING ("
        "id = (SELECT employee_id FROM profiles WHERE id = auth.uid()) "
        "OR (role = 'plant_head' AND plant_id = public.current_employee_plant_id()))"
    )
    op.execute("ALTER TABLE employees DROP COLUMN hire_date")
    op.execute("ALTER TABLE employees DROP COLUMN employment_status")
    op.execute("ALTER TABLE employees DROP COLUMN direct_manager_id")
    op.execute("ALTER TABLE employees DROP COLUMN job_title")
    op.execute("ALTER TABLE employees DROP COLUMN department_id")
    op.execute("ALTER TABLE employees DROP COLUMN employee_code")
    op.execute("DROP TABLE IF EXISTS departments CASCADE")
    op.execute("ALTER TABLE employees DROP CONSTRAINT employees_role_check")
    op.execute(
        "ALTER TABLE employees ADD CONSTRAINT employees_role_check "
        "CHECK (role IN ('supervisor', 'manager', 'plant_head', 'hr_admin', 'recruiter'))"
    )
