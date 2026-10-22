from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app import auth, db
from app.schemas import Line, MachineCreate, MachineReply, MachineSummary

router = APIRouter()
Author = Annotated[dict, Depends(auth.sop_author)]

_SUMMARY_SQL = """
SELECT m.id, m.name, m.line_id, l.name AS line_name,
       s.id AS sop_id, s.version AS sop_version, s.language,
       (SELECT COUNT(*) FROM steps WHERE sop_id = s.id) AS step_count
FROM machines m
JOIN lines l ON l.id = m.line_id
LEFT JOIN sops s ON s.id = (
    SELECT id FROM sops WHERE machine_id = m.id ORDER BY version DESC LIMIT 1
)
"""


def _summary(conn, machine_id: int) -> MachineSummary:
    row = conn.execute(text(f"{_SUMMARY_SQL} WHERE m.id = :machine_id"), {"machine_id": machine_id}).mappings().fetchone()
    return MachineSummary(**row)


@router.get("/machines", response_model=list[MachineSummary])
def list_machines() -> list[MachineSummary]:
    """Every machine with its line and current SOP, for the machine picker. Unauthenticated: a
    worker never needs an account just to see what machines exist and open their SOP cards."""
    with db.connect_service() as conn:
        rows = conn.execute(text(f"{_SUMMARY_SQL} ORDER BY m.id")).mappings().fetchall()
    return [MachineSummary(**r) for r in rows]


@router.get("/machine/{machine_id}/replies", response_model=list[MachineReply])
def list_machine_replies(machine_id: int, limit: int = 20) -> list[MachineReply]:
    """Answers that belong to this machine rather than to one person, newest first.

    Keyed on the machine, not on whoever asked, because a worker has no account to deliver
    anything to (see CLAUDE.md's Auth section). That is the right address for kind 'machine' and
    'sop': "this press is unsafe until maintenance clears it" concerns everyone who walks up to
    it, and delivering it only to the anonymous worker who happened to ask would leave the next
    one to start a faulty machine.

    Kind 'understanding' is excluded: a reply about one worker misreading a step is for that
    worker, and reaches them through their own receipt (GET /api/receipt/{receipt}) instead.
    Returns the reply alone - never the report's summary, kind or severity, which stay
    manager-only.
    """
    with db.connect_service() as conn:
        rows = conn.execute(
            text("""
                SELECT r.id, r.response_text_worker AS text, r.ack_audio_key AS audio_key,
                       r.responded_at, st.step_number
                FROM reports r
                JOIN sops s ON s.id = r.sop_id
                LEFT JOIN steps st ON st.id = r.step_id
                WHERE s.machine_id = :machine_id
                  AND r.answered_by_sop = FALSE
                  AND r.kind IS DISTINCT FROM 'understanding'
                  AND r.ack_audio_key IS NOT NULL
                  AND r.response_text_worker IS NOT NULL
                ORDER BY r.responded_at DESC NULLS LAST, r.id DESC
                LIMIT :limit
            """),
            {"machine_id": machine_id, "limit": limit},
        ).mappings().fetchall()
    return [MachineReply(**r) for r in rows]


@router.post("/machines", response_model=MachineSummary, status_code=201)
def create_machine(req: MachineCreate, person: Author) -> MachineSummary:
    """Add a machine to a line. It starts with no SOP, waiting for a supervisor to record one."""
    with db.connect(person) as conn:
        if not conn.execute(text("SELECT 1 FROM lines WHERE id = :line_id"), {"line_id": req.line_id}).fetchone():
            raise HTTPException(404, "line not found")
        if not auth.may_author_line(person, req.line_id, conn):
            raise HTTPException(403, "that line is not yours")
        machine_id = conn.execute(
            text("INSERT INTO machines (line_id, name) VALUES (:line_id, :name) RETURNING id"),
            {"line_id": req.line_id, "name": req.name},
        ).scalar_one()
        return _summary(conn, machine_id)


@router.get("/lines", response_model=list[Line])
def list_lines(person: Author) -> list[Line]:
    """The lines a new machine can belong to: only the caller's own."""
    if person["role"] == "plant_head":
        where, params = "plant_id = :plant", {"plant": person["plant_id"]}
    else:
        where, params = "supervisor_id = :me OR manager_id = :me", {"me": person["id"]}
    with db.connect(person) as conn:
        rows = conn.execute(text(f"SELECT id, name, plant_id FROM lines WHERE {where} ORDER BY id"), params).mappings().fetchall()
    return [Line(**r) for r in rows]
