"""Make report_view.escalated a real boolean instead of sometimes NULL.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-22

`escalated` was `(r.status = 'open' AND r.escalate_after < now())`. In SQL's three-valued logic
`TRUE AND NULL` is NULL, so any open report with no `escalate_after` yielded NULL rather than
false - and `schemas.Report.escalated` is a non-optional bool, so a single such row made
`GET /api/reports` fail for the whole inbox with a 500, not just for that report.

That state is reachable: app/routes/report.py sets `status = 'open'` in one statement and
routing.route() sets `escalate_after` in a later one, so a failure in between leaves a report
permanently open with escalate_after NULL. Confirmed by actually hitting the 500, not inferred.

`escalate_after IS NOT NULL AND ...` keeps the same meaning - a report with no deadline has not
passed one - while guaranteeing true or false. The downstream `CASE WHEN escalated` is
unaffected (it already treated NULL as not-escalated), and the view is recreated unchanged
otherwise, keeping `security_invoker = true`, which is load-bearing (see CLAUDE.md's Auth
section: without it RLS is evaluated as the view's owner and leaks every row).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_VIEW = """
CREATE VIEW report_view WITH (security_invoker = true) AS
WITH base AS (
    SELECT r.*, m.id AS machine_id, l.id AS line_id, l.plant_id,
           {escalated} AS escalated,
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
"""

_NULL_SAFE = "(r.status = 'open' AND r.escalate_after IS NOT NULL AND r.escalate_after < now())"
_ORIGINAL = "(r.status = 'open' AND r.escalate_after < now())"


def upgrade() -> None:
    op.execute("DROP VIEW report_view")
    op.execute(_VIEW.format(escalated=_NULL_SAFE))


def downgrade() -> None:
    op.execute("DROP VIEW report_view")
    op.execute(_VIEW.format(escalated=_ORIGINAL))
