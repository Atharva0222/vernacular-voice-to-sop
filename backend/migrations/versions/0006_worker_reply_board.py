"""The manager's reply as the worker receives it: translated text plus when it was sent.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-22

`reports.response_text` holds what the manager actually typed or dictated, which may be in any
language (English, in practice). The worker never sees that text - they hear it spoken - so the
translated wording used for TTS was previously thrown away after `tts.synthesize()`, leaving no
record of what the worker was actually told. `response_text_worker` keeps it, so a reply can be
re-voiced later without re-translating and so the manager's own inbox can show what was sent.

`responded_at` is needed because `created_at` is when the *worker* filed the report, not when
the manager answered. The worker-facing reply board on each machine orders by, and displays,
the reply time, so it cannot be derived from what was already here.

No RLS policy changes: both columns sit on `reports`, already covered by 0001's policies, and
the worker-facing read goes through db.connect_service() which bypasses RLS entirely (see
CLAUDE.md's Auth section).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE reports ADD COLUMN response_text_worker TEXT")
    op.execute("ALTER TABLE reports ADD COLUMN responded_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE reports DROP COLUMN responded_at")
    op.execute("ALTER TABLE reports DROP COLUMN response_text_worker")
