import sqlite3


def draft(conn: sqlite3.Connection, report_id: int) -> None:
    """Once a report's cluster is a confirmed 'sop' cluster on a known step, draft one step edit for it
    from the cluster's most recent suggested change."""
    report = conn.execute(
        "SELECT cluster_id, kind, step_id, confirmed FROM report_view WHERE id = ?", (report_id,)
    ).fetchone()
    if not (report["confirmed"] and report["kind"] == "sop" and report["step_id"]):
        return
    suggestion = conn.execute(
        "SELECT suggested_change FROM reports WHERE cluster_id = ? AND suggested_change IS NOT NULL "
        "ORDER BY id DESC LIMIT 1",
        (report["cluster_id"],),
    ).fetchone()
    if not suggestion:
        return
    conn.execute(
        "INSERT OR IGNORE INTO step_edits (cluster_id, sop_id, step_id, old_text, new_text) "
        "SELECT ?, sop_id, id, text, ? FROM steps WHERE id = ?",
        (report["cluster_id"], suggestion["suggested_change"], report["step_id"]),
    )


def approve(conn: sqlite3.Connection, edit: sqlite3.Row) -> int:
    """Write the machine's next SOP version with the edited step swapped in, keep the old version for audit,
    and resolve the cluster's reports. Returns the new SOP id."""
    base = conn.execute(
        "SELECT * FROM sops WHERE machine_id = ? ORDER BY version DESC LIMIT 1", (edit["machine_id"],)
    ).fetchone()
    new_sop_id = conn.execute(
        "INSERT INTO sops (machine_id, title, language, transcript, version) VALUES (?, ?, ?, ?, ?)",
        (base["machine_id"], base["title"], base["language"], base["transcript"], base["version"] + 1),
    ).lastrowid
    conn.execute(
        "INSERT INTO steps (sop_id, step_number, text, is_safety_warning, icon) "
        "SELECT ?, step_number, CASE WHEN step_number = ? THEN ? ELSE text END, is_safety_warning, icon "
        "FROM steps WHERE sop_id = ? ORDER BY step_number",
        (new_sop_id, edit["step_number"], edit["new_text"], base["id"]),
    )
    conn.execute("UPDATE step_edits SET status = 'approved', new_sop_id = ? WHERE id = ?", (new_sop_id, edit["id"]))
    conn.execute("UPDATE reports SET status = 'resolved' WHERE cluster_id = ?", (edit["cluster_id"],))
    return new_sop_id
