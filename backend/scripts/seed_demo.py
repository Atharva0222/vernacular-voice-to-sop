"""Seed richer demo data for the CRM modules (Employee/Workforce/HR) so the staff dashboards have
something to show. `scripts/e2e.py`'s `ensure_demo_org()` only seeds the minimum the checklist
needs (1 plant, 5 people, 2 lines, 1 machine, hardcoded ids) - this adds departments, workers,
SOPs/reports, shifts/attendance, leave and a recruitment pipeline on top of that same org.

Usage (from backend/, against a running Supabase project - local or cloud):
    python scripts/seed_demo.py

Idempotent per section: each block checks for its own existing rows first, so reruns against the
same project are cheap and don't duplicate.
"""
import secrets
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db  # noqa: E402
from scripts.e2e import _signup_or_signin, ensure_demo_org  # noqa: E402

PLANT_ID = 1
TODAY = date.today()
NOW = datetime.now(timezone.utc)

URGENT_SLA_HOURS = 24
DEFAULT_SLA_HOURS = 72


def seed_departments(conn: Connection) -> dict[str, int]:
    existing = conn.execute(text("SELECT name, id FROM departments WHERE plant_id = :p"), {"p": PLANT_ID}).all()
    if existing:
        return {name: id_ for name, id_ in existing}
    rows = conn.execute(
        text(
            "INSERT INTO departments (plant_id, name) VALUES "
            "(:p, 'Production'), (:p, 'Quality'), (:p, 'Maintenance'), (:p, 'HR & Recruitment') "
            "RETURNING name, id"
        ),
        {"p": PLANT_ID},
    ).all()
    print(f"seeded {len(rows)} departments")
    return {name: id_ for name, id_ in rows}


def enrich_core_employees(conn: Connection, dept: dict[str, int]) -> None:
    # (employee_id, job_title, department, hire_date offset in days)
    updates = [
        (1, "Line Supervisor", "Production", 900),
        (2, "Production Manager", "Production", 1500),
        (3, "Plant Head", "Production", 2600),
        (4, "Line Supervisor", "Quality", 700),
        (5, "Production Manager", "Quality", 1300),
    ]
    changed = 0
    for emp_id, title, dname, days_ago in updates:
        result = conn.execute(
            text(
                "UPDATE employees SET job_title = :title, department_id = :dept_id, "
                "employee_code = :code, hire_date = :hire_date "
                "WHERE id = :id AND employee_code IS NULL"
            ),
            {
                "title": title,
                "dept_id": dept[dname],
                "code": f"EMP-{emp_id:04d}",
                "hire_date": TODAY - timedelta(days=days_ago),
                "id": emp_id,
            },
        )
        changed += result.rowcount
    if changed:
        print(f"enriched {changed} core employee directory rows")


EXTRA_STAFF = [
    ("e2e-hr-admin@test.local", "Demo HR Admin", "hr_admin", "HR Administrator"),
    ("e2e-recruiter@test.local", "Demo Recruiter", "recruiter", "Talent Recruiter"),
]


def seed_extra_staff(conn: Connection, dept: dict[str, int]) -> None:
    existing = conn.execute(
        text("SELECT 1 FROM employees WHERE plant_id = :p AND role IN ('hr_admin', 'recruiter')"), {"p": PLANT_ID}
    ).first()
    if existing:
        return
    for email, name, role, title in EXTRA_STAFF:
        emp_id = conn.execute(
            text(
                "INSERT INTO employees (name, role, language, plant_id, department_id, job_title, "
                "employee_code, hire_date) VALUES "
                "(:name, :role, 'hi', :p, :dept_id, :title, :code, :hire_date) RETURNING id"
            ),
            {
                "name": name,
                "role": role,
                "p": PLANT_ID,
                "dept_id": dept["HR & Recruitment"],
                "title": title,
                "code": f"EMP-{900 if role == 'hr_admin' else 901}",
                "hire_date": TODAY - timedelta(days=500),
            },
        ).scalar_one()
        uid = _signup_or_signin(email)
        conn.execute(text("INSERT INTO profiles (id, employee_id) VALUES (:uid, :emp) ON CONFLICT DO NOTHING"), {"uid": uid, "emp": emp_id})
    print(f"seeded {len(EXTRA_STAFF)} extra staff accounts (hr_admin, recruiter)")


WORKERS = [
    ("Ramesh Patil", "Machine Operator", "Production", 2),
    ("Suresh Yadav", "Machine Operator", "Production", 2),
    ("Anita Kamble", "Quality Inspector", "Quality", 5),
    ("Vijay Shinde", "Machine Operator", "Production", 2),
    ("Pooja Jadhav", "Quality Inspector", "Quality", 5),
    ("Sanjay More", "Maintenance Technician", "Maintenance", 2),
    ("Kavita Pawar", "Machine Operator", "Production", 2),
    ("Rahul Deshmukh", "Maintenance Technician", "Maintenance", 5),
    ("Sunita Gaikwad", "Machine Operator", "Production", 2),
    ("Amit Joshi", "Quality Inspector", "Quality", 5),
]


def seed_workers(conn: Connection, dept: dict[str, int]) -> list[int]:
    existing = conn.execute(text("SELECT id FROM employees WHERE plant_id = :p AND role = 'worker' ORDER BY id"), {"p": PLANT_ID}).scalars().all()
    if existing:
        return list(existing)
    ids = []
    for i, (name, title, dname, manager_id) in enumerate(WORKERS):
        emp_id = conn.execute(
            text(
                "INSERT INTO employees (name, role, language, plant_id, department_id, job_title, "
                "employee_code, hire_date, direct_manager_id, employment_status) VALUES "
                "(:name, 'worker', 'hi', :p, :dept_id, :title, :code, :hire_date, :mgr, :status) RETURNING id"
            ),
            {
                "name": name,
                "p": PLANT_ID,
                "dept_id": dept[dname],
                "title": title,
                "code": f"EMP-{200 + i:04d}",
                "hire_date": TODAY - timedelta(days=200 + i * 17),
                "mgr": manager_id,
                "status": "on_leave" if i == 9 else "active",
            },
        ).scalar_one()
        ids.append(emp_id)
    print(f"seeded {len(ids)} worker-role employees")
    return ids


def seed_machine_b(conn: Connection) -> int:
    existing = conn.execute(text("SELECT id FROM machines WHERE line_id = 2")).scalar()
    if existing:
        return existing
    machine_id = conn.execute(text("INSERT INTO machines (line_id, name) VALUES (2, 'Press 2') RETURNING id")).scalar_one()
    print("seeded machine 'Press 2' on line B")
    return machine_id


STEPS = [
    ("बिजली का स्विच बंद करके ही मशीन खोलें।", True, "power_off"),
    ("पैडल को पैर से धीरे धीरे दबाएं।", False, "check"),
    ("सत्रह नंबर का बोल्ट लगाकर प्लेट को कस दें।", False, "moving_parts"),
    ("दस्ताने पहनकर ही प्लेट पकड़ें।", True, "ppe"),
    ("काम खत्म होने के बाद मशीन को साफ करके रिपोर्ट लिखें।", False, "clean"),
]


def seed_sop(conn: Connection, machine_id: int, title: str) -> dict:
    existing_id = conn.execute(text("SELECT id FROM sops WHERE machine_id = :m"), {"m": machine_id}).scalar()
    if existing_id:
        steps = conn.execute(
            text("SELECT id, step_number FROM steps WHERE sop_id = :s ORDER BY step_number"), {"s": existing_id}
        ).mappings().all()
        return {"id": existing_id, "steps": list(steps)}
    sop_id = conn.execute(
        text(
            "INSERT INTO sops (machine_id, title, language, transcript, version) "
            "VALUES (:m, :t, 'hi', :tr, 1) RETURNING id"
        ),
        {"m": machine_id, "t": title, "tr": " ".join(s[0] for s in STEPS)},
    ).scalar_one()
    steps = []
    for i, (step_text, warn, icon) in enumerate(STEPS, start=1):
        step_id = conn.execute(
            text(
                "INSERT INTO steps (sop_id, step_number, text, is_safety_warning, icon) "
                "VALUES (:s, :n, :t, :w, :i) RETURNING id"
            ),
            {"s": sop_id, "n": i, "t": step_text, "w": warn, "i": icon},
        ).scalar_one()
        steps.append({"id": step_id, "step_number": i})
    print(f"seeded SOP '{title}' with {len(steps)} steps")
    return {"id": sop_id, "steps": steps}


def _insert_report(conn: Connection, *, sop_id: int, step_id: int | None, kind: str | None, severity: str | None,
                    status: str, summary: str | None, suggested_change: str | None, error: str | None,
                    assigned_to: int | None, created_at: datetime) -> int:
    escalate_after = None
    if status != "failed" and kind is not None:
        hours = URGENT_SLA_HOURS if (kind == "machine" and severity == "high") else DEFAULT_SLA_HOURS
        escalate_after = created_at + timedelta(hours=hours)
    return conn.execute(
        text(
            "INSERT INTO reports (sop_id, step_id, language, status, kind, summary, severity, "
            "suggested_change, error, assigned_to, escalate_after, receipt, created_at) VALUES "
            "(:sop_id, :step_id, 'hi', :status, :kind, :summary, :severity, :suggested_change, :error, "
            ":assigned_to, :escalate_after, :receipt, :created_at) RETURNING id"
        ),
        {
            "sop_id": sop_id, "step_id": step_id, "status": status, "kind": kind, "summary": summary,
            "severity": severity, "suggested_change": suggested_change, "error": error,
            "assigned_to": assigned_to, "escalate_after": escalate_after,
            "receipt": secrets.token_urlsafe(16), "created_at": created_at,
        },
    ).scalar_one()


def seed_reports(conn: Connection, sop_a: dict, sop_b: dict) -> None:
    if conn.execute(text("SELECT 1 FROM reports LIMIT 1")).first():
        return
    step3_a = sop_a["steps"][2]["id"]  # "17mm bolt" step - the one the sop-kind cluster disputes
    ago = lambda hours: NOW - timedelta(hours=hours)  # noqa: E731

    rows = [
        # Line A (sop_a, manager=2)
        dict(sop_id=sop_a["id"], step_id=None, kind="machine", severity="high", status="open",
             summary="पैडल बहुत ढीला हो गया है, दबाने पर वापस ऊपर नहीं आता - चोट लग सकती है।",
             suggested_change=None, error=None, assigned_to=2, created_at=ago(48)),  # already past 24h SLA -> escalated
        dict(sop_id=sop_a["id"], step_id=None, kind="machine", severity="medium", status="acknowledged",
             summary="मोटर से अजीब आवाज़ आ रही है।", suggested_change=None, error=None, assigned_to=2, created_at=ago(28)),
        dict(sop_id=sop_a["id"], step_id=None, kind="machine", severity="low", status="resolved",
             summary="गार्ड रेल का बोल्ट ढीला था, कस दिया गया।", suggested_change=None, error=None, assigned_to=2, created_at=ago(144)),
        dict(sop_id=sop_a["id"], step_id=step3_a, kind="sop", severity="medium", status="open",
             summary="कार्ड पर सत्रह नंबर का बोल्ट लिखा है लेकिन उन्नीस नंबर का बोल्ट फिट होता है।",
             suggested_change="प्लेट कसने के लिए उन्नीस नंबर का बोल्ट इस्तेमाल करें।", error=None, assigned_to=2, created_at=ago(70)),
        dict(sop_id=sop_a["id"], step_id=step3_a, kind="sop", severity="medium", status="open",
             summary="बोल्ट नंबर कार्ड पर गलत लिखा है, उन्नीस नंबर सही है।",
             suggested_change="प्लेट कसने के लिए उन्नीस नंबर का बोल्ट इस्तेमाल करें।", error=None, assigned_to=2, created_at=ago(46)),
        dict(sop_id=sop_a["id"], step_id=step3_a, kind="sop", severity="medium", status="open",
             summary="फिर से वही शिकायत - सत्रह नहीं उन्नीस नंबर का बोल्ट चाहिए।",
             suggested_change="प्लेट कसने के लिए उन्नीस नंबर का बोल्ट इस्तेमाल करें।", error=None, assigned_to=2, created_at=ago(20)),
        dict(sop_id=sop_a["id"], step_id=None, kind="understanding", severity="low", status="resolved",
             summary="वर्कर को स्टेप का क्रम समझ नहीं आया, समझा दिया गया।", suggested_change=None, error=None,
             assigned_to=2, created_at=ago(96)),
        dict(sop_id=sop_a["id"], step_id=None, kind=None, severity=None, status="failed",
             summary=None, suggested_change=None, error="transcription produced empty text",
             assigned_to=None, created_at=ago(120)),
        # Line B (sop_b, manager=5)
        dict(sop_id=sop_b["id"], step_id=None, kind="machine", severity="high", status="open",
             summary="गार्ड सेंसर ट्रिप नहीं हो रहा है।", suggested_change=None, error=None, assigned_to=5, created_at=ago(12)),
        dict(sop_id=sop_b["id"], step_id=None, kind="machine", severity="medium", status="acknowledged",
             summary="बेस के पास तेल रिस रहा है।", suggested_change=None, error=None, assigned_to=5, created_at=ago(64)),
        dict(sop_id=sop_b["id"], step_id=None, kind="sop", severity="low", status="resolved",
             summary="कार्ड में कूलडाउन का स्टेप नहीं है।", suggested_change="मशीन बंद करने के बाद दो मिनट रुकें।",
             error=None, assigned_to=5, created_at=ago(190)),
        dict(sop_id=sop_b["id"], step_id=None, kind="understanding", severity="low", status="open",
             summary="वर्कर को स्टेप्स का क्रम समझ नहीं आया।", suggested_change=None, error=None, assigned_to=5, created_at=ago(9)),
        dict(sop_id=sop_b["id"], step_id=None, kind="machine", severity="low", status="resolved",
             summary="हल्का कंपन था, जांच की गई - ठीक है।", suggested_change=None, error=None, assigned_to=5, created_at=ago(210)),
        dict(sop_id=sop_b["id"], step_id=None, kind="sop", severity="medium", status="acknowledged",
             summary="माप वाला स्टेप साफ नहीं है।", suggested_change=None, error=None, assigned_to=5, created_at=ago(44)),
    ]

    ids = [_insert_report(conn, **row) for row in rows]
    cluster_reports = ids[3:6]  # the three same-step 'sop' complaints on sop_a
    cluster_id = cluster_reports[0]
    conn.execute(
        text("UPDATE reports SET cluster_id = :c WHERE id = ANY(:ids)"),
        {"c": cluster_id, "ids": cluster_reports},
    )
    # Mirrors corrections.draft(): a confirmed (3+) 'sop' cluster on a known step drafts one
    # pending edit for the Inbox to show, using the cluster's suggested_change.
    conn.execute(
        text(
            "INSERT INTO step_edits (cluster_id, sop_id, step_id, old_text, new_text) "
            "SELECT :cluster_id, sop_id, id, text, :new_text FROM steps WHERE id = :step_id"
        ),
        {"cluster_id": cluster_id, "new_text": "प्लेट कसने के लिए उन्नीस नंबर का बोल्ट इस्तेमाल करें।", "step_id": step3_a},
    )
    print(f"seeded {len(rows)} reports (1 escalated, 1 confirmed cluster with a drafted step edit)")


def seed_shifts(conn: Connection) -> list[dict]:
    existing = conn.execute(
        text("SELECT id, name, starts_at, ends_at FROM shifts WHERE plant_id = :p ORDER BY id"), {"p": PLANT_ID}
    ).mappings().all()
    if existing:
        return list(existing)
    rows = conn.execute(
        text(
            "INSERT INTO shifts (plant_id, name, starts_at, ends_at) VALUES "
            "(:p, 'Morning', :m_start, :m_end), (:p, 'Afternoon', :a_start, :a_end), (:p, 'Night', :n_start, :n_end) "
            "RETURNING id, name, starts_at, ends_at"
        ),
        {
            "p": PLANT_ID,
            "m_start": time(6, 0), "m_end": time(14, 0),
            "a_start": time(14, 0), "a_end": time(22, 0),
            "n_start": time(22, 0), "n_end": time(6, 0),
        },
    ).mappings().all()
    print(f"seeded {len(rows)} shifts")
    return list(rows)


def seed_workforce(conn: Connection, worker_ids: list[int], shifts: list[dict], machine_a: int, machine_b: int) -> None:
    if conn.execute(text("SELECT 1 FROM shift_assignments LIMIT 1")).first():
        return
    line_a_workers, line_b_workers = worker_ids[:5], worker_ids[5:]
    assigned = 0
    attended = 0
    for day_offset in range(4, -1, -1):  # 4 days ago .. today
        work_date = TODAY - timedelta(days=day_offset)
        for i, emp_id in enumerate(line_a_workers):
            shift = shifts[i % len(shifts)]
            assignment_id = conn.execute(
                text(
                    "INSERT INTO shift_assignments (employee_id, shift_id, line_id, work_date) "
                    "VALUES (:e, :s, 1, :d) RETURNING id"
                ),
                {"e": emp_id, "s": shift["id"], "d": work_date},
            ).scalar_one()
            assigned += 1
            if day_offset > 0 or i < 3:  # today: only the first 3 have clocked in so far
                clock_in = datetime.combine(work_date, shift["starts_at"], tzinfo=timezone.utc)
                clock_out = None if day_offset == 0 else datetime.combine(work_date, shift["ends_at"], tzinfo=timezone.utc)
                conn.execute(
                    text("INSERT INTO attendance (shift_assignment_id, clock_in, clock_out, machine_id) VALUES (:a, :ci, :co, :m)"),
                    {"a": assignment_id, "ci": clock_in, "co": clock_out, "m": machine_a},
                )
                attended += 1
        for i, emp_id in enumerate(line_b_workers):
            shift = shifts[(i + 1) % len(shifts)]
            assignment_id = conn.execute(
                text(
                    "INSERT INTO shift_assignments (employee_id, shift_id, line_id, work_date) "
                    "VALUES (:e, :s, 2, :d) RETURNING id"
                ),
                {"e": emp_id, "s": shift["id"], "d": work_date},
            ).scalar_one()
            assigned += 1
            if day_offset > 0 or i < 2:
                clock_in = datetime.combine(work_date, shift["starts_at"], tzinfo=timezone.utc)
                clock_out = None if day_offset == 0 else datetime.combine(work_date, shift["ends_at"], tzinfo=timezone.utc)
                conn.execute(
                    text("INSERT INTO attendance (shift_assignment_id, clock_in, clock_out, machine_id) VALUES (:a, :ci, :co, :m)"),
                    {"a": assignment_id, "ci": clock_in, "co": clock_out, "m": machine_b},
                )
                attended += 1
    print(f"seeded {assigned} shift assignments over 5 days ({attended} with attendance)")


def seed_leave(conn: Connection, staff_ids: list[int], worker_ids: list[int]) -> None:
    if conn.execute(text("SELECT 1 FROM leave_types LIMIT 1")).first():
        return
    types = conn.execute(
        text(
            "INSERT INTO leave_types (name, annual_quota_days) VALUES "
            "('Casual Leave', 12), ('Sick Leave', 10), ('Earned Leave', 15) RETURNING id, name"
        )
    ).mappings().all()
    by_name = {t["name"]: t["id"] for t in types}
    year = TODAY.year
    everyone = staff_ids + worker_ids
    for emp_id in everyone:
        for name, type_id in by_name.items():
            quota = {"Casual Leave": 12, "Sick Leave": 10, "Earned Leave": 15}[name]
            used = (emp_id * 3 + len(name)) % (quota // 2 + 1)
            conn.execute(
                text(
                    "INSERT INTO leave_balances (employee_id, leave_type_id, year, remaining_days) "
                    "VALUES (:e, :t, :y, :r)"
                ),
                {"e": emp_id, "t": type_id, "y": year, "r": quota - used},
            )

    requests = [
        (worker_ids[0], "Casual Leave", 6, 8, "pending", None),
        (worker_ids[2], "Sick Leave", -3, -2, "approved", 3),
        (worker_ids[4], "Earned Leave", 10, 14, "pending", None),
        (worker_ids[6], "Casual Leave", -10, -9, "rejected", 3),
        (staff_ids[0], "Earned Leave", 20, 25, "approved", 3),
        (worker_ids[1], "Sick Leave", 2, 2, "pending", None),
        (worker_ids[8], "Casual Leave", -20, -18, "approved", 5),
    ]
    for emp_id, type_name, start_off, end_off, status, approver in requests:
        conn.execute(
            text(
                "INSERT INTO leave_requests (employee_id, leave_type_id, starts_on, ends_on, status, approved_by) "
                "VALUES (:e, :t, :s, :en, :status, :approver)"
            ),
            {
                "e": emp_id, "t": by_name[type_name],
                "s": TODAY + timedelta(days=start_off), "en": TODAY + timedelta(days=end_off),
                "status": status, "approver": approver,
            },
        )
    print(f"seeded {len(by_name)} leave types, balances for {len(everyone)} employees, {len(requests)} leave requests")


JOB_POSTINGS = [
    ("Press Machine Operator", "Production", "open"),
    ("Quality Inspector", "Quality", "open"),
    ("Maintenance Technician", "Maintenance", "closed"),
]
CANDIDATES = [
    ("Deepak Shah", "9820011122", "deepak.shah@example.com"),
    ("Priya Nair", "9820011123", "priya.nair@example.com"),
    ("Mohammed Ali", "9820011124", "mohammed.ali@example.com"),
    ("Sneha Kulkarni", "9820011125", "sneha.kulkarni@example.com"),
    ("Arjun Mehta", "9820011126", "arjun.mehta@example.com"),
    ("Farah Sheikh", "9820011127", "farah.sheikh@example.com"),
    ("Rohit Verma", "9820011128", "rohit.verma@example.com"),
    ("Neha Choudhary", "9820011129", "neha.choudhary@example.com"),
]
# index into CANDIDATES, posting index, stage
APPLICATIONS = [
    (0, 0, "applied"), (1, 0, "screening"), (2, 0, "interview"), (3, 0, "offer"),
    (4, 1, "applied"), (5, 1, "screening"), (6, 1, "hired"),
    (7, 2, "rejected"),
]


def seed_recruitment(conn: Connection, dept: dict[str, int], created_by: int) -> None:
    if conn.execute(text("SELECT 1 FROM job_postings LIMIT 1")).first():
        return
    posting_ids = []
    for title, dname, status in JOB_POSTINGS:
        pid = conn.execute(
            text(
                "INSERT INTO job_postings (plant_id, title, department_id, status, created_by) "
                "VALUES (:p, :title, :dept_id, :status, :by) RETURNING id"
            ),
            {"p": PLANT_ID, "title": title, "dept_id": dept[dname], "status": status, "by": created_by},
        ).scalar_one()
        posting_ids.append(pid)

    candidate_ids = []
    for name, phone, email in CANDIDATES:
        cid = conn.execute(
            text("INSERT INTO candidates (name, phone, email) VALUES (:n, :p, :e) RETURNING id"),
            {"n": name, "p": phone, "e": email},
        ).scalar_one()
        candidate_ids.append(cid)

    for cand_idx, posting_idx, stage in APPLICATIONS:
        conn.execute(
            text("INSERT INTO applications (job_posting_id, candidate_id, stage) VALUES (:j, :c, :stage)"),
            {"j": posting_ids[posting_idx], "c": candidate_ids[cand_idx], "stage": stage},
        )
    print(f"seeded {len(posting_ids)} job postings, {len(candidate_ids)} candidates, {len(APPLICATIONS)} applications")


def main() -> None:
    ensure_demo_org()
    with db.connect_service() as conn:
        dept = seed_departments(conn)
        enrich_core_employees(conn, dept)
        seed_extra_staff(conn, dept)
        worker_ids = seed_workers(conn, dept)
        machine_b = seed_machine_b(conn)
        sop_a = seed_sop(conn, 1, "Press 1")
        sop_b = seed_sop(conn, machine_b, "Press 2")
        seed_reports(conn, sop_a, sop_b)
        shifts = seed_shifts(conn)
        seed_workforce(conn, worker_ids, shifts, machine_a=1, machine_b=machine_b)
        seed_leave(conn, staff_ids=[1, 2, 3, 4, 5], worker_ids=worker_ids)
        seed_recruitment(conn, dept, created_by=3)
    print("\ndemo data ready - sign in as e2e-person3@test.local (Demo Plant Head) to see everything")


if __name__ == "__main__":
    main()
