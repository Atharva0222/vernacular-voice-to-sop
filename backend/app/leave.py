from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.engine import Connection


def approve(conn: Connection, request: Mapping, approver_id: int) -> None:
    """Deduct the requested days from the employee's balance for that leave type and year, and
    mark the request approved. Mirrors app.corrections.approve()'s shape: takes an already
    fetched (and already scope-checked) row, does one focused state transition plus its
    side effect - no existence/status checks here, the route already did those."""
    days = (request["ends_on"] - request["starts_on"]).days + 1
    year = request["starts_on"].year
    conn.execute(
        text(
            "UPDATE leave_balances SET remaining_days = remaining_days - :days "
            "WHERE employee_id = :employee_id AND leave_type_id = :leave_type_id AND year = :year"
        ),
        {"days": days, "employee_id": request["employee_id"], "leave_type_id": request["leave_type_id"], "year": year},
    )
    conn.execute(
        text("UPDATE leave_requests SET status = 'approved', approved_by = :approver WHERE id = :id"),
        {"approver": approver_id, "id": request["id"]},
    )
