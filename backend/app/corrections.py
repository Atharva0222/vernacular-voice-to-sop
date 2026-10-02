from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.engine import Connection


def draft(conn: Connection, report_id: int) -> None:
    """Once a report's cluster is a confirmed 'sop' cluster on a known step, draft one step edit for it
    from the cluster's most recent suggested change."""
    report = (
        conn.execute(
            text("SELECT cluster_id, kind, step_id, confirmed FROM report_view WHERE id = :id"),
            {"id": report_id},
        )
        .mappings()
        .fetchone()
    )
    if not (report["confirmed"] and report["kind"] == "sop" and report["step_id"]):
        return
    suggestion = (
        conn.execute(
            text(
                "SELECT suggested_change FROM reports WHERE cluster_id = :cluster_id "
                "AND suggested_change IS NOT NULL ORDER BY id DESC LIMIT 1"
            ),
            {"cluster_id": report["cluster_id"]},
        )
        .mappings()
        .fetchone()
    )
    if not suggestion:
        return
    conn.execute(
        text(
            "INSERT INTO step_edits (cluster_id, sop_id, step_id, old_text, new_text) "
            "SELECT :cluster_id, sop_id, id, text, :new_text FROM steps WHERE id = :step_id "
            "ON CONFLICT (cluster_id) DO NOTHING"
        ),
        {"cluster_id": report["cluster_id"], "new_text": suggestion["suggested_change"], "step_id": report["step_id"]},
    )


def approve(conn: Connection, edit: Mapping) -> int:
    """Write the machine's next SOP version with the edited step swapped in, keep the old version for audit,
    and resolve the cluster's reports. Returns the new SOP id."""
    base = (
        conn.execute(
            text("SELECT * FROM sops WHERE machine_id = :machine_id ORDER BY version DESC LIMIT 1"),
            {"machine_id": edit["machine_id"]},
        )
        .mappings()
        .fetchone()
    )
    new_sop_id = conn.execute(
        text(
            "INSERT INTO sops (machine_id, title, language, transcript, version) "
            "VALUES (:machine_id, :title, :language, :transcript, :version) RETURNING id"
        ),
        {
            "machine_id": base["machine_id"],
            "title": base["title"],
            "language": base["language"],
            "transcript": base["transcript"],
            "version": base["version"] + 1,
        },
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO steps (sop_id, step_number, text, is_safety_warning, icon) "
            "SELECT :new_sop_id, step_number, "
            "CASE WHEN step_number = :step_number THEN :new_text ELSE text END, is_safety_warning, icon "
            "FROM steps WHERE sop_id = :base_sop_id ORDER BY step_number"
        ),
        {
            "new_sop_id": new_sop_id,
            "step_number": edit["step_number"],
            "new_text": edit["new_text"],
            "base_sop_id": base["id"],
        },
    )
    conn.execute(
        text("UPDATE step_edits SET status = 'approved', new_sop_id = :new_sop_id WHERE id = :id"),
        {"new_sop_id": new_sop_id, "id": edit["id"]},
    )
    conn.execute(
        text("UPDATE reports SET status = 'resolved' WHERE cluster_id = :cluster_id"),
        {"cluster_id": edit["cluster_id"]},
    )
    return new_sop_id
