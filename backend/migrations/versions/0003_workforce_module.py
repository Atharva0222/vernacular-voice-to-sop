"""workforce module: shifts, shift assignments, attendance

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03

Authority model deliberately splits in two, mirroring how SOPs/machines already work:
- `shifts` (shift *definitions*, e.g. "Morning 06:00-14:00") are plant-wide scheduling config,
  so writing them uses the same hr_admin/plant_head gate as departments (0002).
- `shift_assignments`/`attendance` (who works which shift, on which line, and their clock
  in/out) are line-scoped operational data, so they reuse the exact `may_author_line` shape
  already established for SOPs: a plant_head covers their whole plant, a supervisor/manager
  only the lines they run.

Clock-in/out is kiosk-style (a supervisor operates it on behalf of a named worker), not a new
anonymous worker-facing route - it requires `line_id`, not the worker's own identity, so it
stays behind normal staff auth like everything else in this module.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LINE_SCOPE = """
    EXISTS (
        SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
        JOIN lines l ON l.id = {table}.line_id
        WHERE p.id = auth.uid()
        AND (e.role = 'plant_head' AND e.plant_id = l.plant_id OR l.supervisor_id = e.id OR l.manager_id = e.id)
    )
"""


def upgrade() -> None:
    op.execute("""
        CREATE TABLE shifts (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            plant_id BIGINT NOT NULL REFERENCES plants(id),
            name TEXT NOT NULL,
            starts_at TIME NOT NULL,
            ends_at TIME NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE shift_assignments (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            employee_id BIGINT NOT NULL REFERENCES employees(id),
            shift_id BIGINT NOT NULL REFERENCES shifts(id),
            line_id BIGINT NOT NULL REFERENCES lines(id),
            work_date DATE NOT NULL,
            UNIQUE (employee_id, work_date)
        )
    """)
    op.execute("""
        CREATE TABLE attendance (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            shift_assignment_id BIGINT NOT NULL UNIQUE REFERENCES shift_assignments(id),
            clock_in TIMESTAMPTZ,
            clock_out TIMESTAMPTZ,
            machine_id BIGINT REFERENCES machines(id)
        )
    """)

    for table in ("shifts", "shift_assignments", "attendance"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        "CREATE POLICY shifts_select ON shifts FOR SELECT TO authenticated "
        "USING (plant_id = public.current_employee_plant_id())"
    )
    op.execute(f"""
        CREATE POLICY shifts_admin_insert ON shifts FOR INSERT TO authenticated WITH CHECK (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                WHERE p.id = auth.uid() AND (e.role = 'hr_admin' OR e.role = 'plant_head')
                AND e.plant_id = shifts.plant_id
            )
        )
    """)

    op.execute(f"CREATE POLICY shift_assignments_author_select ON shift_assignments FOR SELECT TO authenticated USING ({_LINE_SCOPE.format(table='shift_assignments')})")
    op.execute(f"CREATE POLICY shift_assignments_author_insert ON shift_assignments FOR INSERT TO authenticated WITH CHECK ({_LINE_SCOPE.format(table='shift_assignments')})")

    # attendance has no line_id of its own - scope joins through its shift_assignment.
    attendance_scope = """
        EXISTS (
            SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
            JOIN shift_assignments sa ON sa.id = attendance.shift_assignment_id
            JOIN lines l ON l.id = sa.line_id
            WHERE p.id = auth.uid()
            AND (e.role = 'plant_head' AND e.plant_id = l.plant_id OR l.supervisor_id = e.id OR l.manager_id = e.id)
        )
    """
    op.execute(f"CREATE POLICY attendance_author_select ON attendance FOR SELECT TO authenticated USING ({attendance_scope})")
    op.execute(f"CREATE POLICY attendance_author_insert ON attendance FOR INSERT TO authenticated WITH CHECK ({attendance_scope})")
    op.execute(f"CREATE POLICY attendance_author_update ON attendance FOR UPDATE TO authenticated USING ({attendance_scope})")

    op.execute("GRANT SELECT, INSERT ON shifts TO authenticated")
    op.execute("GRANT SELECT, INSERT ON shift_assignments TO authenticated")
    op.execute("GRANT SELECT, INSERT, UPDATE ON attendance TO authenticated")
    op.execute("GRANT ALL ON shifts, shift_assignments, attendance TO service_role")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS attendance CASCADE")
    op.execute("DROP TABLE IF EXISTS shift_assignments CASCADE")
    op.execute("DROP TABLE IF EXISTS shifts CASCADE")
