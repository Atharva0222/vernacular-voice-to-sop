from fastapi import APIRouter, HTTPException

from app import db
from app.schemas import Line, MachineCreate, MachineSummary

router = APIRouter()

_SUMMARY_SQL = """
SELECT m.id, m.name, l.name AS line_name,
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
def create_machine(req: MachineCreate) -> MachineSummary:
    """Add a machine to a line. It starts with no SOP, waiting for a supervisor to record one."""
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM lines WHERE id = ?", (req.line_id,)).fetchone():
            raise HTTPException(404, "line not found")
        machine_id = conn.execute(
            "INSERT INTO machines (line_id, name) VALUES (?, ?)", (req.line_id, req.name)
        ).lastrowid
        return _summary(conn, machine_id)


@router.get("/lines", response_model=list[Line])
def list_lines() -> list[Line]:
    """The lines a new machine can belong to."""
    with db.connect() as conn:
        rows = conn.execute("SELECT id, name, plant_id FROM lines ORDER BY id").fetchall()
    return [Line(**r) for r in rows]
