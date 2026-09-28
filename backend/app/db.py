import sqlite3
from contextlib import contextmanager

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS plants (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('supervisor', 'manager', 'plant_head')),
    phone TEXT,
    language TEXT NOT NULL DEFAULT 'hi',
    plant_id INTEGER NOT NULL REFERENCES plants(id),
    pin_hash TEXT
);
CREATE TABLE IF NOT EXISTS lines (
    id INTEGER PRIMARY KEY,
    plant_id INTEGER NOT NULL REFERENCES plants(id),
    name TEXT NOT NULL,
    supervisor_id INTEGER NOT NULL REFERENCES people(id),
    manager_id INTEGER NOT NULL REFERENCES people(id)
);
CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY,
    line_id INTEGER NOT NULL REFERENCES lines(id),
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sops (
    id INTEGER PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines(id),
    title TEXT NOT NULL,
    language TEXT NOT NULL,
    transcript TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY,
    sop_id INTEGER NOT NULL REFERENCES sops(id),
    step_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    is_safety_warning INTEGER NOT NULL,
    icon TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    sop_id INTEGER NOT NULL REFERENCES sops(id),
    step_id INTEGER REFERENCES steps(id),
    language TEXT,
    status TEXT NOT NULL DEFAULT 'received',
    kind TEXT,
    summary TEXT,
    severity TEXT,
    suggested_change TEXT,
    error TEXT,
    response_text TEXT,
    ack_audio_key TEXT,
    answered_by_sop INTEGER NOT NULL DEFAULT 0,
    assigned_to INTEGER REFERENCES people(id),
    escalate_after TEXT,
    cluster_id INTEGER,
    receipt TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS reports_escalate_after ON reports(escalate_after);
CREATE INDEX IF NOT EXISTS reports_cluster_id ON reports(cluster_id);

-- Escalation and cluster size are computed on read, so there is no scheduler that can stop.
-- Questions the SOP itself answered never enter this view: they stay between the worker and
-- their machine, so speaking up is never something a manager can see.
CREATE VIEW IF NOT EXISTS report_view AS
WITH base AS (
    SELECT r.*, m.id AS machine_id, l.id AS line_id, l.plant_id,
           r.status = 'open' AND r.escalate_after < strftime('%Y-%m-%dT%H:%M:%SZ', 'now') AS escalated,
           (SELECT COUNT(*) FROM reports c WHERE c.cluster_id = r.cluster_id) AS cluster_count
    FROM reports r
    JOIN sops s ON s.id = r.sop_id
    JOIN machines m ON m.id = s.machine_id
    JOIN lines l ON l.id = m.line_id
    WHERE r.answered_by_sop = 0
)
SELECT base.*,
       CASE WHEN escalated
            THEN (SELECT id FROM people WHERE role = 'plant_head' AND plant_id = base.plant_id ORDER BY id LIMIT 1)
            ELSE assigned_to END AS effective_assignee,
       MAX(cluster_count, 1) AS cluster_size,
       cluster_count >= 3 AS confirmed
FROM base;

-- One drafted step edit per confirmed 'sop' cluster, awaiting a manager's approve/reject.
CREATE TABLE IF NOT EXISTS step_edits (
    id INTEGER PRIMARY KEY,
    cluster_id INTEGER NOT NULL UNIQUE,
    sop_id INTEGER NOT NULL REFERENCES sops(id),
    step_id INTEGER NOT NULL REFERENCES steps(id),
    old_text TEXT NOT NULL,
    new_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    new_sop_id INTEGER REFERENCES sops(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE VIEW IF NOT EXISTS step_edit_view AS
SELECT e.*, s.machine_id, st.step_number, l.id AS line_id, l.plant_id,
       (SELECT COUNT(*) FROM reports r WHERE r.cluster_id = e.cluster_id) AS report_count
FROM step_edits e
JOIN sops s ON s.id = e.sop_id
JOIN steps st ON st.id = e.step_id
JOIN machines m ON m.id = s.machine_id
JOIN lines l ON l.id = m.line_id;
"""

DEMO_ORG = """
INSERT INTO plants (id, name) VALUES (1, 'Demo Plant');
INSERT INTO people (id, name, role, language, plant_id) VALUES
    (1, 'Demo Supervisor', 'supervisor', 'hi', 1),
    (2, 'Demo Manager', 'manager', 'hi', 1),
    (3, 'Demo Plant Head', 'plant_head', 'hi', 1),
    (4, 'Demo Supervisor B', 'supervisor', 'mr', 1),
    (5, 'Demo Manager B', 'manager', 'mr', 1);
INSERT INTO lines (id, plant_id, name, supervisor_id, manager_id) VALUES
    (1, 1, 'Line A', 1, 2),
    (2, 1, 'Line B', 4, 5);
INSERT INTO machines (id, line_id, name) VALUES (1, 1, 'Press 1'), (2, 2, 'Lathe 1');
"""

DEMO_PINS = {1: "1111", 2: "2222", 3: "3333", 4: "4444", 5: "5555"}


@contextmanager
def connect():
    """Yield a connection that commits on success and always closes."""
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init() -> None:
    """Create tables, and seed a demo org with known PINs on an empty database."""
    from app import auth  # deferred: auth imports this module

    with connect() as conn:
        conn.executescript(SCHEMA)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(people)")}
        if "pin_hash" not in cols:
            conn.execute("ALTER TABLE people ADD COLUMN pin_hash TEXT")
        if conn.execute("SELECT COUNT(*) FROM plants").fetchone()[0] == 0:
            conn.executescript(DEMO_ORG)
            conn.executemany(
                "UPDATE people SET pin_hash = ? WHERE id = ?",
                [(auth.hash_pin(pin), person_id) for person_id, pin in DEMO_PINS.items()],
            )
