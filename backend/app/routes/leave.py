from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app import auth, db, leave
from app.schemas import (
    LeaveBalance,
    LeaveBalanceSet,
    LeaveRequest,
    LeaveRequestCreate,
    LeaveRequestStatus,
    LeaveType,
    LeaveTypeCreate,
)

router = APIRouter()
Staff = Annotated[dict, Depends(auth.sop_author)]
Admin = Annotated[dict, Depends(auth.org_admin)]

_REQUEST_SQL = """
SELECT r.id, r.employee_id, e.name AS employee_name, r.leave_type_id, lt.name AS leave_type_name,
       r.starts_on, r.ends_on, r.status, r.approved_by, r.created_at
FROM leave_requests r
JOIN employees e ON e.id = r.employee_id
JOIN leave_types lt ON lt.id = r.leave_type_id
"""


@router.get("/leave-types", response_model=list[LeaveType])
def list_leave_types(_person: Staff) -> list[LeaveType]:
    with db.connect(_person) as conn:
        rows = conn.execute(text("SELECT id, name, annual_quota_days FROM leave_types ORDER BY name")).mappings().fetchall()
    return [LeaveType(**r) for r in rows]


@router.post("/leave-types", response_model=LeaveType, status_code=201)
def create_leave_type(req: LeaveTypeCreate, person: Annotated[dict, Depends(auth.current_person)]) -> LeaveType:
    if person["role"] != "hr_admin":
        raise HTTPException(403, "only HR admins define leave types")
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "INSERT INTO leave_types (name, annual_quota_days) VALUES (:name, :annual_quota_days) "
                "RETURNING id, name, annual_quota_days"
            ),
            req.model_dump(),
        ).mappings().fetchone()
    return LeaveType(**row)


@router.get("/leave-balances", response_model=list[LeaveBalance])
def list_leave_balances(person: Staff, employee_id: int | None = None, year: int | None = None) -> list[LeaveBalance]:
    """Defaults to the caller's own balance; hr_admin/plant_head may pass employee_id for
    anyone in their plant - RLS is what actually enforces that, not this default."""
    target = employee_id if employee_id is not None else person["id"]
    with db.connect(person) as conn:
        rows = conn.execute(
            text(
                "SELECT employee_id, leave_type_id, year, remaining_days FROM leave_balances "
                "WHERE employee_id = :employee_id AND (CAST(:year AS int) IS NULL OR year = :year)"
            ),
            {"employee_id": target, "year": year},
        ).mappings().fetchall()
    return [LeaveBalance(**r) for r in rows]


@router.post("/leave-balances", response_model=LeaveBalance, status_code=201)
def set_leave_balance(req: LeaveBalanceSet, person: Admin) -> LeaveBalance:
    """Upsert: HR sets a balance directly rather than this computing an annual accrual - a
    real accrual engine is out of scope for this MVP (see migration 0004's docstring)."""
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "INSERT INTO leave_balances (employee_id, leave_type_id, year, remaining_days) "
                "VALUES (:employee_id, :leave_type_id, :year, :remaining_days) "
                "ON CONFLICT (employee_id, leave_type_id, year) DO UPDATE SET remaining_days = :remaining_days "
                "RETURNING employee_id, leave_type_id, year, remaining_days"
            ),
            req.model_dump(),
        ).mappings().fetchone()
    return LeaveBalance(**row)


def _get_request(conn, request_id: int):
    row = conn.execute(text(f"{_REQUEST_SQL} WHERE r.id = :id"), {"id": request_id}).mappings().fetchone()
    if not row:
        raise HTTPException(404, "leave request not found")
    return row


@router.get("/leave-requests", response_model=list[LeaveRequest])
def list_leave_requests(person: Staff, status: LeaveRequestStatus | None = None) -> list[LeaveRequest]:
    """The caller's own requests, plus - for hr_admin/plant_head - everyone else's in their
    plant (RLS enforces the split; this route does not branch on role)."""
    with db.connect(person) as conn:
        rows = conn.execute(
            text(
                f"SELECT * FROM ({_REQUEST_SQL}) AS r "
                "WHERE (CAST(:status AS text) IS NULL OR status = :status) ORDER BY created_at DESC"
            ),
            {"status": status},
        ).mappings().fetchall()
    return [LeaveRequest(**r) for r in rows]


@router.post("/leave-requests", response_model=LeaveRequest, status_code=201)
def create_leave_request(req: LeaveRequestCreate, person: Staff) -> LeaveRequest:
    """Self-service only: the caller always requests leave for themselves. Workers (role
    'worker') have no account and so cannot use this - see migration 0004's docstring for why
    that is an explicit MVP scope line, not an oversight."""
    with db.connect(person) as conn:
        request_id = conn.execute(
            text(
                "INSERT INTO leave_requests (employee_id, leave_type_id, starts_on, ends_on) "
                "VALUES (:employee_id, :leave_type_id, :starts_on, :ends_on) RETURNING id"
            ),
            {"employee_id": person["id"], **req.model_dump()},
        ).scalar_one()
        row = _get_request(conn, request_id)
    return LeaveRequest(**row)


@router.post("/leave-requests/{request_id}/approve", response_model=LeaveRequest)
def approve_leave_request(request_id: int, person: Admin) -> LeaveRequest:
    with db.connect(person) as conn:
        row = _get_request(conn, request_id)
        if row["status"] != "pending":
            raise HTTPException(409, f"leave request already {row['status']}")
        leave.approve(conn, row, person["id"])
        row = _get_request(conn, request_id)
    return LeaveRequest(**row)


@router.post("/leave-requests/{request_id}/reject", response_model=LeaveRequest)
def reject_leave_request(request_id: int, person: Admin) -> LeaveRequest:
    with db.connect(person) as conn:
        row = _get_request(conn, request_id)
        if row["status"] != "pending":
            raise HTTPException(409, f"leave request already {row['status']}")
        conn.execute(text("UPDATE leave_requests SET status = 'rejected' WHERE id = :id"), {"id": request_id})
        row = _get_request(conn, request_id)
    return LeaveRequest(**row)
