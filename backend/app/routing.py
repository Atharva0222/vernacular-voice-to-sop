from sqlalchemy import text
from sqlalchemy.engine import Connection

URGENT_SLA_HOURS = 24
DEFAULT_SLA_HOURS = 72
CLUSTER_WINDOW_DAYS = 30


def route(conn: Connection, report_id: int) -> None:
    """Assign a triaged report to its line's manager (never the supervisor) and set its SLA deadline."""
    conn.execute(
        text(
            """
            UPDATE reports SET
                assigned_to = (SELECT l.manager_id FROM sops s
                               JOIN machines m ON m.id = s.machine_id
                               JOIN lines l ON l.id = m.line_id
                               WHERE s.id = reports.sop_id),
                escalate_after = created_at + make_interval(hours =>
                    CASE WHEN kind = 'machine' AND severity = 'high' THEN :urgent ELSE :default END)
            WHERE id = :id
            """
        ),
        {"id": report_id, "urgent": URGENT_SLA_HOURS, "default": DEFAULT_SLA_HOURS},
    )


def cluster(conn: Connection, report_id: int) -> None:
    """Link a report to an unresolved earlier one on the same machine, kind and step within the window."""
    match = (
        conn.execute(
            text(
                """
                SELECT o.id, o.cluster_id FROM report_view r
                JOIN report_view o ON o.machine_id = r.machine_id AND o.kind = r.kind
                    AND o.step_id IS NOT DISTINCT FROM r.step_id
                WHERE r.id = :id AND o.id != r.id
                  AND o.status IN ('open', 'acknowledged')
                  AND o.created_at >= r.created_at - make_interval(days => :window)
                ORDER BY o.id LIMIT 1
                """
            ),
            {"id": report_id, "window": CLUSTER_WINDOW_DAYS},
        )
        .mappings()
        .fetchone()
    )
    if not match:
        return
    cluster_id = match["cluster_id"] or match["id"]
    conn.execute(
        text("UPDATE reports SET cluster_id = :cluster_id WHERE id IN (:a, :b)"),
        {"cluster_id": cluster_id, "a": match["id"], "b": report_id},
    )
