from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException

from app import auth, corrections, db
from app.schemas import SOPCreate, SOPSummary, StepEdit, StoredSOP

router = APIRouter()
Reader = Annotated[dict, Depends(auth.report_reader)]

_SUMMARY_COLS = "id, machine_id, title, language, version, created_at"


@router.post("/sop", response_model=StoredSOP)
def create_sop(req: SOPCreate) -> StoredSOP:
    """Persist a generated SOP as the next version for its machine."""
    with db.connect() as conn:
        if not conn.execute("SELECT 1 FROM machines WHERE id = ?", (req.machine_id,)).fetchone():
            raise HTTPException(404, "machine not found")
        version = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM sops WHERE machine_id = ?", (req.machine_id,)
        ).fetchone()[0]
        sop_id = conn.execute(
            "INSERT INTO sops (machine_id, title, language, transcript, version) VALUES (?, ?, ?, ?, ?)",
            (req.machine_id, req.title, req.language, req.transcript, version),
        ).lastrowid
        conn.executemany(
            "INSERT INTO steps (sop_id, step_number, text, is_safety_warning, icon) VALUES (?, ?, ?, ?, ?)",
            [(sop_id, s.step_number, s.text, s.is_safety_warning, s.icon) for s in req.steps],
        )
    return get_sop(sop_id)


@router.get("/sop/{sop_id}", response_model=StoredSOP)
def get_sop(sop_id: int) -> StoredSOP:
    with db.connect() as conn:
        sop = conn.execute(f"SELECT {_SUMMARY_COLS}, transcript FROM sops WHERE id = ?", (sop_id,)).fetchone()
        if not sop:
            raise HTTPException(404, "SOP not found")
        steps = conn.execute(
            "SELECT id, step_number, text, is_safety_warning, icon FROM steps WHERE sop_id = ? ORDER BY step_number",
            (sop_id,),
        ).fetchall()
    return StoredSOP(**sop, steps=[dict(s) for s in steps])


@router.get("/sops", response_model=list[SOPSummary])
def list_sops() -> list[SOPSummary]:
    with db.connect() as conn:
        rows = conn.execute(f"SELECT {_SUMMARY_COLS} FROM sops ORDER BY id DESC").fetchall()
    return [SOPSummary(**r) for r in rows]


@router.get("/machine/{machine_id}/sop", response_model=StoredSOP)
def current_sop(machine_id: int) -> StoredSOP:
    """The machine's current SOP: its highest version. What the worker's cards show."""
    with db.connect() as conn:
        row = conn.execute("SELECT id FROM sops WHERE machine_id = ? ORDER BY version DESC LIMIT 1", (machine_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no SOP for this machine")
    return get_sop(row["id"])


def _visible_edit(conn, edit_id: int, person: dict):
    where, params = auth.scope_sql(person)
    edit = conn.execute(f"SELECT * FROM step_edit_view WHERE id = :id AND {where}", {"id": edit_id, **params}).fetchone()
    if not edit:
        raise HTTPException(404, "step edit not found")
    if edit["status"] != "pending":
        raise HTTPException(409, f"step edit already {edit['status']}")
    return edit


@router.get("/step-edits", response_model=list[StepEdit])
def list_step_edits(person: Reader, status: Literal["pending", "approved", "rejected"] = "pending") -> list[StepEdit]:
    """Card changes drafted from confirmed worker reports, as old/new text for approve/reject."""
    where, params = auth.scope_sql(person)
    with db.connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM step_edit_view WHERE {where} AND status = :status ORDER BY id DESC",
            {"status": status, **params},
        ).fetchall()
    return [StepEdit(**r) for r in rows]


@router.post("/step-edit/{edit_id}/approve", response_model=StoredSOP)
def approve_step_edit(edit_id: int, person: Reader) -> StoredSOP:
    with db.connect() as conn:
        new_sop_id = corrections.approve(conn, _visible_edit(conn, edit_id, person))
    return get_sop(new_sop_id)


@router.post("/step-edit/{edit_id}/reject", status_code=204)
def reject_step_edit(edit_id: int, person: Reader) -> None:
    with db.connect() as conn:
        _visible_edit(conn, edit_id, person)
        conn.execute("UPDATE step_edits SET status = 'rejected' WHERE id = ?", (edit_id,))
