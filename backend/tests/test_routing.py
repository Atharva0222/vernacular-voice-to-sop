import secrets
from datetime import UTC, datetime

from app import routing


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _insert_sop(conn, machine_id: int) -> int:
    return conn.execute(
        "INSERT INTO sops (machine_id, title, language, transcript, version) VALUES (?, 'T', 'hi', 'x', 1)",
        (machine_id,),
    ).lastrowid


def _insert_report(conn, sop_id: int, *, kind="machine", severity="high", status="open", created_at=None) -> int:
    created_at = created_at or _iso(datetime.now(UTC))
    return conn.execute(
        "INSERT INTO reports (sop_id, status, kind, severity, receipt, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (sop_id, status, kind, severity, secrets.token_hex(8), created_at),
    ).lastrowid


def test_route_assigns_lines_manager_not_supervisor(conn):
    # Machine 1 is on Line A: supervisor_id=1, manager_id=2 (app/db.py DEMO_ORG).
    sop_id = _insert_sop(conn, machine_id=1)
    report_id = _insert_report(conn, sop_id, kind="machine", severity="high")
    routing.route(conn, report_id)
    row = conn.execute(
        "SELECT assigned_to, escalate_after, created_at FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    assert row["assigned_to"] == 2
    assert row["escalate_after"] > row["created_at"]


def test_route_urgent_sla_is_shorter_than_default(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    urgent_id = _insert_report(conn, sop_id, kind="machine", severity="high")
    routine_id = _insert_report(conn, sop_id, kind="sop", severity="low")
    routing.route(conn, urgent_id)
    routing.route(conn, routine_id)
    urgent_deadline = conn.execute("SELECT escalate_after FROM reports WHERE id = ?", (urgent_id,)).fetchone()[0]
    routine_deadline = conn.execute("SELECT escalate_after FROM reports WHERE id = ?", (routine_id,)).fetchone()[0]
    assert urgent_deadline < routine_deadline


def test_cluster_links_matching_open_reports_on_same_machine_kind_step(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    first = _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    second = _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    routing.cluster(conn, second)
    rows = {
        r["id"]: r["cluster_id"]
        for r in conn.execute("SELECT id, cluster_id FROM reports WHERE id IN (?, ?)", (first, second))
    }
    assert rows[first] == rows[second] == first


def test_cluster_does_not_link_different_kind(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    second = _insert_report(conn, sop_id, kind="machine", severity="medium", status="open")
    routing.cluster(conn, second)
    row = conn.execute("SELECT cluster_id FROM reports WHERE id = ?", (second,)).fetchone()
    assert row["cluster_id"] is None


def test_cluster_does_not_link_resolved_reports(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    _insert_report(conn, sop_id, kind="sop", severity="medium", status="resolved")
    second = _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    routing.cluster(conn, second)
    row = conn.execute("SELECT cluster_id FROM reports WHERE id = ?", (second,)).fetchone()
    assert row["cluster_id"] is None
