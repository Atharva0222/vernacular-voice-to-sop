from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import auth, db
from app.schemas import Line, MachineCreate, MachineSummary

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
    row = conn.execute(f"{_SUMMARY_SQL} WHERE m.id = ?", (machine_id,)).fetchone()
    return MachineSummary(**row)


@router.get("/machines", response_model=list[MachineSummary])
def list_machines() -> list[MachineSummary]:
    """Every machine with its line and current SOP, for the machine picker."""
    with db.connect() as conn:
        rows = conn.execute(f"{_SUMMARY_SQL} ORDER BY m.id").fetchall()
    return [MachineSummary(**r) for r in rows]


@router.post("/machines", response_model=MachineSummary, status_code=201)
def create_machine(req: MachineCreate, person: Author) -> MachineSummary:
    """Add a machine to a line. It starts with no SOP, waiting for a supervisor to record one."""
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM lines WHERE id = ?", (req.line_id,)).fetchone():
            raise HTTPException(404, "line not found")
        if not auth.may_author_line(person, req.line_id, conn):
            raise HTTPException(403, "that line is not yours")
        machine_id = conn.execute(
            "INSERT INTO machines (line_id, name) VALUES (?, ?)", (req.line_id, req.name)
        ).lastrowid
        return _summary(conn, machine_id)


@router.get("/lines", response_model=list[Line])
def list_lines(person: Author) -> list[Line]:
    """The lines a new machine can belong to: only the caller's own."""
    if person["role"] == "plant_head":
        where, params = "plant_id = :plant", {"plant": person["plant_id"]}
    else:
        where, params = "supervisor_id = :me OR manager_id = :me", {"me": person["id"]}
    with db.connect() as conn:
        rows = conn.execute(f"SELECT id, name, plant_id FROM lines WHERE {where} ORDER BY id", params).fetchall()
    return [Line(**r) for r in rows]
