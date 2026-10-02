from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app import auth, db
from app.schemas import (
    Department,
    DepartmentCreate,
    EmployeeCreate,
    EmployeeSummary,
    EmployeeUpdate,
    EmploymentStatus,
)

router = APIRouter()
Staff = Annotated[dict, Depends(auth.sop_author)]
Admin = Annotated[dict, Depends(auth.org_admin)]

_EMPLOYEE_COLS = (
    "id, name, role, phone, language, plant_id, employee_code, department_id, job_title, "
    "direct_manager_id, employment_status, hire_date, created_at"
)


@router.get("/employees", response_model=list[EmployeeSummary])
def list_employees(
    person: Staff, department_id: int | None = None, employment_status: EmploymentStatus | None = None
) -> list[EmployeeSummary]:
    """The plant's directory - every role including workers tracked for shift scheduling.
    RLS already limits this to the caller's own plant; the filters below are convenience."""
    with db.connect(person) as conn:
        rows = conn.execute(
            text(
                f"SELECT {_EMPLOYEE_COLS} FROM employees "
                "WHERE plant_id = :plant_id "
                "AND (CAST(:department_id AS bigint) IS NULL OR department_id = :department_id) "
                "AND (CAST(:employment_status AS text) IS NULL OR employment_status = :employment_status) "
                "ORDER BY name"
            ),
            {"plant_id": person["plant_id"], "department_id": department_id, "employment_status": employment_status},
        ).mappings().fetchall()
    return [EmployeeSummary(**r) for r in rows]


@router.get("/employees/{employee_id}", response_model=EmployeeSummary)
def get_employee(employee_id: int, person: Staff) -> EmployeeSummary:
    with db.connect(person) as conn:
        row = conn.execute(
            text(f"SELECT {_EMPLOYEE_COLS} FROM employees WHERE id = :id"), {"id": employee_id}
        ).mappings().fetchone()
    if not row:
        raise HTTPException(404, "employee not found")
    return EmployeeSummary(**row)


@router.post("/employees", response_model=EmployeeSummary, status_code=201)
def create_employee(req: EmployeeCreate, person: Admin) -> EmployeeSummary:
    """Adds a directory row only - this does not provision sign-in access. Granting a
    supervisor/manager/plant_head/hr_admin/recruiter an account is a separate, deliberately
    manual step (create their Supabase Auth user, then link it via `profiles`), not part of
    this MVP's UI - most rows created here (role='worker') never get an account at all."""
    with db.connect(person) as conn:
        employee_id = conn.execute(
            text(
                "INSERT INTO employees (name, role, phone, language, plant_id, employee_code, "
                "department_id, job_title, direct_manager_id, hire_date) "
                "VALUES (:name, :role, :phone, :language, :plant_id, :employee_code, "
                ":department_id, :job_title, :direct_manager_id, :hire_date) RETURNING id"
            ),
            {**req.model_dump(), "plant_id": person["plant_id"]},
        ).scalar_one()
    return get_employee(employee_id, person)


@router.patch("/employees/{employee_id}", response_model=EmployeeSummary)
def update_employee(employee_id: int, req: EmployeeUpdate, person: Admin) -> EmployeeSummary:
    fields = req.model_dump(exclude_none=True)
    if fields:
        with db.connect(person) as conn:
            result = conn.execute(
                text(f"UPDATE employees SET {', '.join(f'{k} = :{k}' for k in fields)} WHERE id = :id"),
                {**fields, "id": employee_id},
            )
            if result.rowcount == 0:
                raise HTTPException(404, "employee not found")
    return get_employee(employee_id, person)


@router.get("/departments", response_model=list[Department])
def list_departments(person: Staff) -> list[Department]:
    with db.connect(person) as conn:
        rows = conn.execute(
            text("SELECT id, plant_id, name, head_employee_id FROM departments WHERE plant_id = :plant_id ORDER BY name"),
            {"plant_id": person["plant_id"]},
        ).mappings().fetchall()
    return [Department(**r) for r in rows]


@router.post("/departments", response_model=Department, status_code=201)
def create_department(req: DepartmentCreate, person: Admin) -> Department:
    with db.connect(person) as conn:
        row = conn.execute(
            text(
                "INSERT INTO departments (plant_id, name, head_employee_id) "
                "VALUES (:plant_id, :name, :head_employee_id) "
                "RETURNING id, plant_id, name, head_employee_id"
            ),
            {"plant_id": person["plant_id"], "name": req.name, "head_employee_id": req.head_employee_id},
        ).mappings().fetchone()
    return Department(**row)
