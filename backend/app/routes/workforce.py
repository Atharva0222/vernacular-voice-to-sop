from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import auth, db
from app.schemas import (
    Attendance,
    ClockIn,
    Shift,
    ShiftAssignment,
    ShiftAssignmentCreate,
    ShiftCreate,
)

router = APIRouter()
Staff = Annotated[dict, Depends(auth.sop_author)]
Admin = Annotated[dict, Depends(auth.org_admin)]

_ASSIGNMENT_SQL = """
SELECT sa.id, sa.employee_id, e.name AS employee_name, sa.shift_id, s.name AS shift_name,
       sa.line_id, sa.work_date, l.plant_id
FROM shift_assignments sa
JOIN employees e ON e.id = sa.employee_id
JOIN shifts s ON s.id = sa.shift_id
JOIN lines l ON l.id = sa.line_id
"""


@router.get("/shifts", response_model=list[Shift])
def list_shifts(person: Staff) -> list[Shift]:
    """Shift definitions (e.g. "Morning 06:00-14:00") are plant-wide, not per line."""
    with db.connect(person) as conn:
        rows = conn.execute(
            text("SELECT id, plant_id, name, starts_at, ends_at FROM shifts WHERE plant_id = :plant_id ORDER BY starts_at"),
            {"plant_id": person["plant_id"]},
        ).mappings().fetchall()
    return [Shift(**r) for r in rows]


@router.post("/shifts", response_model=Shift, status_code=201)
def create_shift(req: ShiftCreate, person: Admin) -> Shift:
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "INSERT INTO shifts (plant_id, name, starts_at, ends_at) "
                "VALUES (:plant_id, :name, :starts_at, :ends_at) "
                "RETURNING id, plant_id, name, starts_at, ends_at"
            ),
            {"plant_id": person["plant_id"], **req.model_dump()},
        ).mappings().fetchone()
    return Shift(**row)


def _get_assignment(conn, assignment_id: int) -> ShiftAssignment:
    row = conn.execute(text(f"{_ASSIGNMENT_SQL} WHERE sa.id = :id"), {"id": assignment_id}).mappings().fetchone()
    if not row:
        raise HTTPException(404, "shift assignment not found")
    return ShiftAssignment(**row)


@router.get("/shift-assignments", response_model=list[ShiftAssignment])
def list_shift_assignments(person: Staff, line_id: int | None = None, work_date: str | None = None) -> list[ShiftAssignment]:
    """The roster for the caller's own lines (or the whole plant for a plant head) - same
    author scope as SOPs/machines, since a shift assignment is just as line-specific."""
    where, params = auth.author_scope_sql(person)
    with db.connect(person) as conn:
        rows = conn.execute(
            text(
                f"SELECT * FROM ({_ASSIGNMENT_SQL}) AS scoped WHERE {where} "
                "AND (CAST(:line_id AS bigint) IS NULL OR line_id = :line_id) "
                "AND (CAST(:work_date AS date) IS NULL OR work_date = CAST(:work_date AS date)) "
                "ORDER BY work_date DESC, id DESC"
            ),
            {"line_id": line_id, "work_date": work_date, **params},
        ).mappings().fetchall()
    return [ShiftAssignment(**r) for r in rows]


@router.post("/shift-assignments", response_model=ShiftAssignment, status_code=201)
def create_shift_assignment(req: ShiftAssignmentCreate, person: Staff) -> ShiftAssignment:
    with db.connect(person) as conn:
        if not auth.may_author_line(person, req.line_id, conn):
            raise HTTPException(403, "that line is not yours")
        try:
            assignment_id = conn.execute(
                text(
                    "INSERT INTO shift_assignments (employee_id, shift_id, line_id, work_date) "
                    "VALUES (:employee_id, :shift_id, :line_id, :work_date) RETURNING id"
                ),
                req.model_dump(),
            ).scalar_one()
        except IntegrityError as exc:
            raise HTTPException(409, "that employee already has a shift assigned that day") from exc
        return _get_assignment(conn, assignment_id)


@router.post("/attendance/clock-in", response_model=Attendance, status_code=201)
def clock_in(req: ClockIn, person: Staff) -> Attendance:
    """Kiosk-style: a supervisor/manager clocks a named worker in on a shared device. Behind
    normal staff auth, not a new worker-facing anonymous route - unlike a problem report, a
    clock-in is inherently tied to one specific person's identity."""
    with db.connect(person) as conn:
        assignment = conn.execute(
            text("SELECT line_id FROM shift_assignments WHERE id = :id"), {"id": req.shift_assignment_id}
        ).mappings().fetchone()
        if not assignment:
            raise HTTPException(404, "shift assignment not found")
        if not auth.may_author_line(person, assignment["line_id"], conn):
            raise HTTPException(403, "that line is not yours")
        try:
            row = conn.execute(
                text(
                    "INSERT INTO attendance (shift_assignment_id, clock_in, machine_id) "
                    "VALUES (:shift_assignment_id, now(), :machine_id) "
                    "RETURNING id, shift_assignment_id, clock_in, clock_out, machine_id"
                ),
                {"shift_assignment_id": req.shift_assignment_id, "machine_id": req.machine_id},
            ).mappings().fetchone()
        except IntegrityError as exc:
            raise HTTPException(409, "already clocked in for this shift") from exc
    return Attendance(**row)


@router.post("/attendance/{attendance_id}/clock-out", response_model=Attendance)
def clock_out(attendance_id: int, person: Staff) -> Attendance:
    """No separate scope check here (unlike clock-in): RLS alone gates the UPDATE, so a
    mismatched attendance id simply matches zero rows - the same 404-not-403 "don't leak
    existence" shape report.py already uses."""
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "UPDATE attendance SET clock_out = now() WHERE id = :id "
                "RETURNING id, shift_assignment_id, clock_in, clock_out, machine_id"
            ),
            {"id": attendance_id},
        ).mappings().fetchone()
    if not row:
        raise HTTPException(404, "attendance record not found")
    return Attendance(**row)
