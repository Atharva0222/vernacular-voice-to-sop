"""Per-step images: a nullable storage path on `steps`, uploaded by the authoring supervisor
via a signed Supabase Storage URL (same pattern as candidate resumes in 0004), plus the RLS
UPDATE policy that pattern needs.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-22

`steps` previously had only SELECT (open to any authenticated staff) and INSERT (line-scoped,
mirroring auth.may_author_line()) policies - rows were meant to be immutable, a new SOP version
inserts new step rows rather than editing old ones. Attaching an image after the fact is the
first legitimate in-place edit, so this adds a `steps_author_update` policy with the exact same
line-scoping predicate as `steps_author_insert`, plus the UPDATE table grant RLS policies alone
don't substitute for (0001's `GRANT SELECT, INSERT ON machines, sops, steps TO authenticated`
never included UPDATE).

Images themselves live in a *public* Supabase Storage bucket (`step-illustrations`, see
app/config.py's storage_step_image_bucket) - not private like candidate-resumes - because the
worker's SOP card is loaded with no auth at all (see CLAUDE.md's Auth section), and that page
needs to hit the image URL directly with no signed-read round trip through the backend. Bucket
creation itself isn't DDL (Storage buckets aren't provisioned via migration in this project even
for candidate-resumes - see 0004's docstring); it's created once against the live project
by the same means candidate-resumes was.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LINE_SCOPED_AUTHOR = """
    EXISTS (
        SELECT 1 FROM profiles p JOIN employees e ON e.id = p.employee_id
        JOIN sops s ON s.id = steps.sop_id
        JOIN machines m ON m.id = s.machine_id JOIN lines l ON l.id = m.line_id
        WHERE p.id = auth.uid()
        AND (e.role = 'plant_head' AND e.plant_id = l.plant_id
             OR l.supervisor_id = e.id OR l.manager_id = e.id)
    )
"""


def upgrade() -> None:
    op.execute("ALTER TABLE steps ADD COLUMN image_path TEXT")

    op.execute(f"""
        CREATE POLICY steps_author_update ON steps FOR UPDATE TO authenticated
        USING ({_LINE_SCOPED_AUTHOR}) WITH CHECK ({_LINE_SCOPED_AUTHOR})
    """)
    op.execute("GRANT UPDATE ON steps TO authenticated")


def downgrade() -> None:
    op.execute("REVOKE UPDATE ON steps FROM authenticated")
    op.execute("DROP POLICY IF EXISTS steps_author_update ON steps")
    op.execute("ALTER TABLE steps DROP COLUMN image_path")
