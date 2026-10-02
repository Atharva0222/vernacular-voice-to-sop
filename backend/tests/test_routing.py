import secrets

from sqlalchemy import text

from app import routing


def _insert_sop(conn, machine_id: int) -> int:
    return conn.execute(
        text("INSERT INTO sops (machine_id, title, language, transcript, version) VALUES (:m, 'T', 'hi', 'x', 1) RETURNING id"),
        {"m": machine_id},
    ).scalar_one()


def _insert_report(conn, sop_id: int, *, kind="machine", severity="high", status="open") -> int:
    return conn.execute(
        text(
            "INSERT INTO reports (sop_id, status, kind, severity, receipt) "
            "VALUES (:sop_id, :status, :kind, :severity, :receipt) RETURNING id"
        ),
        {"sop_id": sop_id, "status": status, "kind": kind, "severity": severity, "receipt": secrets.token_hex(8)},
    ).scalar_one()


def test_route_assigns_lines_manager_not_supervisor(conn):
    # Machine 1 is on Line A: supervisor_id=1, manager_id=2 (tests/conftest.py's demo org).
    sop_id = _insert_sop(conn, machine_id=1)
    report_id = _insert_report(conn, sop_id, kind="machine", severity="high")
    routing.route(conn, report_id)
    row = conn.execute(
        text("SELECT assigned_to, escalate_after, created_at FROM reports WHERE id = :id"), {"id": report_id}
    ).mappings().fetchone()
    assert row["assigned_to"] == 2
    assert row["escalate_after"] > row["created_at"]


def test_route_urgent_sla_is_shorter_than_default(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    urgent_id = _insert_report(conn, sop_id, kind="machine", severity="high")
    routine_id = _insert_report(conn, sop_id, kind="sop", severity="low")
    routing.route(conn, urgent_id)
    routing.route(conn, routine_id)
    urgent_deadline = conn.execute(text("SELECT escalate_after FROM reports WHERE id = :id"), {"id": urgent_id}).scalar_one()
    routine_deadline = conn.execute(text("SELECT escalate_after FROM reports WHERE id = :id"), {"id": routine_id}).scalar_one()
    assert urgent_deadline < routine_deadline


def test_cluster_links_matching_open_reports_on_same_machine_kind_step(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    first = _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    second = _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    routing.cluster(conn, second)
    rows = {
        r["id"]: r["cluster_id"]
        for r in conn.execute(
            text("SELECT id, cluster_id FROM reports WHERE id IN (:a, :b)"), {"a": first, "b": second}
        ).mappings()
    }
    assert rows[first] == rows[second] == first


def test_cluster_does_not_link_different_kind(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    second = _insert_report(conn, sop_id, kind="machine", severity="medium", status="open")
    routing.cluster(conn, second)
    row = conn.execute(text("SELECT cluster_id FROM reports WHERE id = :id"), {"id": second}).mappings().fetchone()
    assert row["cluster_id"] is None


def test_cluster_does_not_link_resolved_reports(conn):
    sop_id = _insert_sop(conn, machine_id=1)
    _insert_report(conn, sop_id, kind="sop", severity="medium", status="resolved")
    second = _insert_report(conn, sop_id, kind="sop", severity="medium", status="open")
    routing.cluster(conn, second)
    row = conn.execute(text("SELECT cluster_id FROM reports WHERE id = :id"), {"id": second}).mappings().fetchone()
    assert row["cluster_id"] is None
