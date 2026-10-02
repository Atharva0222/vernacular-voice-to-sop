"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-01

Mirrors app/db.py's SCHEMA exactly (imported, not copied, so the two can never drift).
`db.init()` still auto-creates and seeds this same schema for local dev/demo convenience
via CREATE TABLE/VIEW IF NOT EXISTS, so running the app without alembic keeps working;
this revision is the versioned, production-style path for applying it going forward.
"""

from collections.abc import Sequence

from alembic import op

from app.db import SCHEMA

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# None of these statements contain an embedded ";", so splitting on it is safe and keeps
# each CREATE run as its own op.execute() call (SQLite's DBAPI only accepts one statement
# at a time through SQLAlchemy's execute, unlike sqlite3.executescript()).
_STATEMENTS = [s.strip() for s in SCHEMA.split(";") if s.strip()]

_DOWNGRADE_ORDER = (
    "step_edit_view",  # view, drop before the tables it selects from
    "step_edits",
    "report_view",  # view
    "reports",
    "steps",
    "sops",
    "machines",
    "lines",
    "people",
    "plants",
)


def upgrade() -> None:
    for statement in _STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for name in _DOWNGRADE_ORDER:
        kind = "VIEW" if name.endswith("_view") else "TABLE"
        op.execute(f"DROP {kind} IF EXISTS {name}")
