"""postgres baseline: core schema, profiles, RLS

Revision ID: 0001
Revises:
Create Date: 2026-10-02

Hand-written Postgres DDL - the old trick of importing and `;`-splitting app.db.SCHEMA (a
SQLite DDL string) doesn't survive the move off SQLite, so every revision from here on is
plain SQL written directly in its migration, with no shared "source of truth" constant.

Covers the pre-existing plants/people(renamed employees)/lines/machines/sops/steps/reports/
step_edits schema translated for Postgres, plus the new `profiles` table bridging Supabase
Auth to `employees`, and the RLS policies that make `authenticated`-role access respect the
same scoping app.auth.scope_sql()/author_scope_sql() already compute in Python - RLS is a
backstop here, not a replacement (see app/auth.py, app/db.py).

Two things verified against a real local Supabase instance before writing this (not assumed
from memory - see conversation history / PR description):
  1. `report_view`/`step_edit_view` MUST be created `WITH (security_invoker = true)`. Without
     it, Postgres evaluates RLS policies on the underlying tables as the VIEW'S OWNER (this
     migration's role), not the querying role - which silently leaks every row to every
     `authenticated` caller regardless of the policies below. This was confirmed to actually
     leak data in a throwaway reproduction, not just inferred from docs.
  2. A plain psycopg/SQLAlchemy connection (not going through PostgREST) has to manually do
     what PostgREST does automatically per request: `SET LOCAL ROLE authenticated` plus
     `SELECT set_config('request.jwt.claims', '...', true)` before `auth.uid()` resolves inside
     policies. See app/db.py's `connect()`.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES_FOR_RLS = (
    "plants",
    "employees",
    "lines",
    "machines",
    "sops",
    "steps",
    "reports",
    "step_edits",
    "profiles",
)


def upgrade() -> None:
    # --- core tables ---------------------------------------------------------------
    op.execute("""
        CREATE TABLE plants (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE employees (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('supervisor', 'manager', 'plant_head', 'hr_admin', 'recruiter')),
            phone TEXT,
            language TEXT NOT NULL DEFAULT 'hi',
            plant_id BIGINT NOT NULL REFERENCES plants(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE lines (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            plant_id BIGINT NOT NULL REFERENCES plants(id),
            name TEXT NOT NULL,
            supervisor_id BIGINT NOT NULL REFERENCES employees(id),
            manager_id BIGINT NOT NULL REFERENCES employees(id)
        )
    """)
    op.execute("""
        CREATE TABLE machines (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            line_id BIGINT NOT NULL REFERENCES lines(id),
            name TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE sops (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            machine_id BIGINT NOT NULL REFERENCES machines(id),
            title TEXT NOT NULL,
            language TEXT NOT NULL,
            transcript TEXT NOT NULL,
            version INT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE steps (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            sop_id BIGINT NOT NULL REFERENCES sops(id),
            step_number INT NOT NULL,
            text TEXT NOT NULL,
            is_safety_warning BOOLEAN NOT NULL,
            icon TEXT NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE reports (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            sop_id BIGINT NOT NULL REFERENCES sops(id),
            step_id BIGINT REFERENCES steps(id),
            language TEXT,
            status TEXT NOT NULL DEFAULT 'received',
            kind TEXT,
            summary TEXT,
            severity TEXT,
            suggested_change TEXT,
            error TEXT,
            response_text TEXT,
            ack_audio_key TEXT,
            answered_by_sop BOOLEAN NOT NULL DEFAULT FALSE,
            assigned_to BIGINT REFERENCES employees(id),
            escalate_after TIMESTAMPTZ,
            cluster_id BIGINT,
            receipt TEXT NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX reports_escalate_after ON reports(escalate_after)")
    op.execute("CREATE INDEX reports_cluster_id ON reports(cluster_id)")

    # One drafted step edit per confirmed 'sop' cluster, awaiting a manager's approve/reject.
    op.execute("""
        CREATE TABLE step_edits (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            cluster_id BIGINT NOT NULL UNIQUE,
            sop_id BIGINT NOT NULL REFERENCES sops(id),
            step_id BIGINT NOT NULL REFERENCES steps(id),
            old_text TEXT NOT NULL,
            new_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
            new_sop_id BIGINT REFERENCES sops(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # --- Supabase Auth bridge --------------------------------------------------------
    # Deliberately thin: it exists only to answer "which auth.uid() is which employees.id".
    # Every FK elsewhere stays a plain bigint; only this one table deals in Supabase's UUIDs.
    op.execute("""
        CREATE TABLE profiles (
            id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
            employee_id BIGINT NOT NULL UNIQUE REFERENCES employees(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # --- views -------------------------------------------------------------------
    # Escalation and cluster size are computed on read, so there is no scheduler that can stop.
    # Questions the SOP itself answered never enter this view: they stay between the worker and
    # their machine, so speaking up is never something a manager can see.
    op.execute("""
        CREATE VIEW report_view WITH (security_invoker = true) AS
        WITH base AS (
            SELECT r.*, m.id AS machine_id, l.id AS line_id, l.plant_id,
                   (r.status = 'open' AND r.escalate_after < now()) AS escalated,
                   (SELECT COUNT(*) FROM reports c WHERE c.cluster_id = r.cluster_id) AS cluster_count
            FROM reports r
            JOIN sops s ON s.id = r.sop_id
            JOIN machines m ON m.id = s.machine_id
            JOIN lines l ON l.id = m.line_id
            WHERE r.answered_by_sop = FALSE
        )
        SELECT base.*,
               CASE WHEN escalated
                    THEN (SELECT id FROM employees WHERE role = 'plant_head' AND plant_id = base.plant_id ORDER BY id LIMIT 1)
                    ELSE assigned_to END AS effective_assignee,
               GREATEST(cluster_count, 1) AS cluster_size,
               (cluster_count >= 3) AS confirmed
        FROM base
    """)
    op.execute("""
        CREATE VIEW step_edit_view WITH (security_invoker = true) AS
        SELECT e.*, s.machine_id, st.step_number, l.id AS line_id, l.plant_id,
               (SELECT COUNT(*) FROM reports r WHERE r.cluster_id = e.cluster_id) AS report_count
        FROM step_edits e
        JOIN sops s ON s.id = e.sop_id
        JOIN steps st ON st.id = e.step_id
        JOIN machines m ON m.id = s.machine_id
        JOIN lines l ON l.id = m.line_id
    """)

    # --- row level security --------------------------------------------------------
    for table in _TABLES_FOR_RLS:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # plants/lines/machines/sops/steps: SOP content is public-by-id today (a worker reads any
    # machine's SOP with no login at all via the service_role connection), so `authenticated`
    # gets the same open SELECT - the real gate on these tables is who may *write* them.
    for table in ("plants", "lines", "machines", "sops", "steps"):
        op.execute(f"CREATE POLICY {table}_select_all ON {table} FOR SELECT TO authenticated USING (true)")

    # machines/sops/steps INSERT: mirrors auth.may_author_line() - a plant_head covers their
    # whole plant, anyone else only the lines they supervise or manage. This is a backstop:
    # app code already checks may_author_line() before issuing these inserts.
    op.execute("""
        CREATE POLICY machines_author_insert ON machines FOR INSERT TO authenticated WITH CHECK (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                JOIN lines l ON l.id = machines.line_id
                WHERE p.id = auth.uid()
                AND (e.role = 'plant_head' AND e.plant_id = l.plant_id
                     OR l.supervisor_id = e.id OR l.manager_id = e.id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY sops_author_insert ON sops FOR INSERT TO authenticated WITH CHECK (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                JOIN machines m ON m.id = sops.machine_id JOIN lines l ON l.id = m.line_id
                WHERE p.id = auth.uid()
                AND (e.role = 'plant_head' AND e.plant_id = l.plant_id
                     OR l.supervisor_id = e.id OR l.manager_id = e.id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY steps_author_insert ON steps FOR INSERT TO authenticated WITH CHECK (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                JOIN sops s ON s.id = steps.sop_id
                JOIN machines m ON m.id = s.machine_id JOIN lines l ON l.id = m.line_id
                WHERE p.id = auth.uid()
                AND (e.role = 'plant_head' AND e.plant_id = l.plant_id
                     OR l.supervisor_id = e.id OR l.manager_id = e.id)
            )
        )
    """)

    # reports/step_edits: the one place worker anonymity meets manager scoping. `authenticated`
    # only ever reads/updates through report_view/step_edit_view's scope - it never inserts a
    # report directly (that only ever happens via the service_role-connected worker routes).
    # Mirrors scope_sql() exactly, plus report_reader()'s supervisor exclusion, so RLS enforces
    # the *combined* authorization logic, not just the WHERE-clause half of it.
    op.execute("""
        CREATE POLICY reports_scope_select ON reports FOR SELECT TO authenticated USING (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                JOIN sops s ON s.id = reports.sop_id JOIN machines m ON m.id = s.machine_id JOIN lines l ON l.id = m.line_id
                WHERE p.id = auth.uid() AND e.role != 'supervisor'
                AND (e.role = 'plant_head' AND e.plant_id = l.plant_id OR l.manager_id = e.id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY reports_scope_update ON reports FOR UPDATE TO authenticated USING (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                JOIN sops s ON s.id = reports.sop_id JOIN machines m ON m.id = s.machine_id JOIN lines l ON l.id = m.line_id
                WHERE p.id = auth.uid() AND e.role != 'supervisor'
                AND (e.role = 'plant_head' AND e.plant_id = l.plant_id OR l.manager_id = e.id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY step_edits_scope_select ON step_edits FOR SELECT TO authenticated USING (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                JOIN sops s ON s.id = step_edits.sop_id JOIN machines m ON m.id = s.machine_id JOIN lines l ON l.id = m.line_id
                WHERE p.id = auth.uid() AND e.role != 'supervisor'
                AND (e.role = 'plant_head' AND e.plant_id = l.plant_id OR l.manager_id = e.id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY step_edits_scope_update ON step_edits FOR UPDATE TO authenticated USING (
            EXISTS (
                SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
                JOIN sops s ON s.id = step_edits.sop_id JOIN machines m ON m.id = s.machine_id JOIN lines l ON l.id = m.line_id
                WHERE p.id = auth.uid() AND e.role != 'supervisor'
                AND (e.role = 'plant_head' AND e.plant_id = l.plant_id OR l.manager_id = e.id)
            )
        )
    """)

    # employees: a signed-in staff member can always read their own row (current_person() needs
    # this), plus any plant_head in their own plant (report_view's escalation lookup needs to
    # resolve a plant_head who may not be the querying user). Broader directory access comes
    # with the Employee module's own migration later.
    #
    # The plant_head branch needs the *caller's own* plant_id, which naively means querying
    # employees from within an employees policy - Postgres re-evaluates the same policy for
    # that inner query and recurses infinitely (confirmed by actually hitting
    # "infinite recursion detected in policy for relation employees" against a real instance).
    # A SECURITY DEFINER function breaks the cycle: it runs as this migration's (RLS-bypassing)
    # owner, so the lookup inside it never re-triggers the policy on the outer query.
    op.execute("""
        CREATE FUNCTION public.current_employee_plant_id() RETURNS BIGINT
        LANGUAGE sql SECURITY DEFINER STABLE SET search_path = public AS $$
            SELECT e.plant_id FROM profiles p JOIN employees e ON e.id = p.employee_id WHERE p.id = auth.uid()
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.current_employee_plant_id() FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.current_employee_plant_id() TO authenticated")
    op.execute("""
        CREATE POLICY employees_scoped_select ON employees FOR SELECT TO authenticated USING (
            id = (SELECT employee_id FROM profiles WHERE id = auth.uid())
            OR (role = 'plant_head' AND plant_id = public.current_employee_plant_id())
        )
    """)

    # profiles: a user may read their own bridge row (needed to resolve employee_id at all).
    op.execute("CREATE POLICY profiles_self_select ON profiles FOR SELECT TO authenticated USING (id = auth.uid())")

    # --- grants ----------------------------------------------------------------------
    # security_invoker views check table-level grants against the *invoking* role, not the view
    # owner - so `authenticated` needs direct grants on every table the views touch, not just
    # the views themselves. Scoped to exactly what each role's routes actually do today.
    op.execute("GRANT USAGE ON SCHEMA public TO authenticated, service_role")
    op.execute("GRANT SELECT ON plants, employees, profiles, lines TO authenticated")
    op.execute("GRANT SELECT, INSERT ON machines, sops, steps TO authenticated")
    op.execute("GRANT SELECT, UPDATE ON reports, step_edits TO authenticated")
    op.execute("GRANT SELECT ON report_view, step_edit_view TO authenticated")
    op.execute(f"GRANT ALL ON {', '.join(_TABLES_FOR_RLS)} TO service_role")
    op.execute("GRANT SELECT ON report_view, step_edit_view TO service_role")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated, service_role")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.current_employee_plant_id() CASCADE")
    for name in (
        "step_edit_view",
        "report_view",
        "profiles",
        "step_edits",
        "reports",
        "steps",
        "sops",
        "machines",
        "lines",
        "employees",
        "plants",
    ):
        kind = "VIEW" if name.endswith("_view") else "TABLE"
        op.execute(f"DROP {kind} IF EXISTS {name} CASCADE")
