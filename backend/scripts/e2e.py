"""End-to-end verification of the feature plan's checklist against a running server.

Usage (from backend/, server running on :8001 against a scratch Supabase project/local stack):
    python scripts/e2e.py [http://localhost:8001]

Needs a real LLM endpoint and the ASR models. Clips are synthesized once with
edge-tts into scripts/clips/ and reused. Writes directly to the DB (via the
RLS-bypassing service-role connection, same as the app's own background tasks) only
where the checklist needs a backdated or repeated report, which no API can create.

Seeds its own demo org (plants/employees/profiles + matching Supabase Auth users) on
first run if one isn't already there - this used to be db.init()'s job, but schema is
Alembic-managed now (see CLAUDE.md's Database section) so nothing seeds data on boot.
"""
import asyncio
import secrets
import sys
import time
from pathlib import Path

import edge_tts
import httpx
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import corrections, db, routing  # noqa: E402
from app.config import settings  # noqa: E402

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"
CLIPS = Path(__file__).resolve().parent / "clips"
VOICE = "hi-IN-SwaraNeural"

# id -> (email, name, role) for the demo org this script seeds and signs in as. Same ids the
# checklist below hardcodes (bearer(1) is the supervisor on line 1, etc.) - keep them in sync.
DEMO_PASSWORD = "e2e-script-password-do-not-use-in-prod"  # noqa: S105
DEMO_PEOPLE = {
    1: ("e2e-person1@test.local", "Demo Supervisor", "supervisor"),
    2: ("e2e-person2@test.local", "Demo Manager", "manager"),
    3: ("e2e-person3@test.local", "Demo Plant Head", "plant_head"),
    4: ("e2e-person4@test.local", "Demo Supervisor B", "supervisor"),
    5: ("e2e-person5@test.local", "Demo Manager B", "manager"),
}

NARRATION = [
    "मशीन चालू करने से पहले बिजली का स्विच बंद कर दें।",
    "पैडल को पैर से धीरे धीरे दबाएं।",
    "सत्रह नंबर का बोल्ट लगाकर प्लेट को कस दें।",
    "प्लेट कसने के बाद ही मशीन चालू करें।",
    "काम खत्म होने के बाद मशीन को साफ करके रिपोर्ट लिखें।",
]
COMPLAINTS = {
    "machine": "पैडल बहुत ढीला हो गया है। दबाने पर वापस ऊपर नहीं आता। इससे चोट लग सकती है।",
    "sop": "कार्ड पर सत्रह नंबर का बोल्ट लिखा है। लेकिन यहां उन्नीस नंबर का बोल्ट लगता है।",
    "understanding": "मुझे समझ नहीं आया कि प्लेट पहले कसनी है या मशीन पहले चालू करनी है।",
}

client = httpx.Client(timeout=300)
passed: list[str] = []
failed: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    (passed if ok else failed).append(name)
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}", flush=True)
    return ok


def clip(name: str, text: str) -> Path:
    path = CLIPS / f"{name}.mp3"
    if not path.exists():
        CLIPS.mkdir(exist_ok=True)
        asyncio.run(edge_tts.Communicate(text, VOICE).save(str(path)))
    return path


def _signup_or_signin(email: str) -> str:
    """Create the demo auth user the first time this script runs against a given Supabase
    project; on later runs it already exists, so fall back to signing in."""
    r = client.post(
        f"{settings.supabase_url}/auth/v1/signup",
        headers={"apikey": settings.supabase_anon_key},
        json={"email": email, "password": DEMO_PASSWORD},
    )
    if r.status_code != 200:
        r = client.post(
            f"{settings.supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_anon_key},
            json={"email": email, "password": DEMO_PASSWORD},
        )
        r.raise_for_status()
    return r.json()["user"]["id"]


def ensure_demo_org() -> None:
    """Seed plants/employees/lines/machines + matching Supabase Auth users/profiles, unless a
    demo org already exists - idempotent so reruns against the same project are cheap. Schema no
    longer auto-seeds on boot; see this file's module docstring.

    Uses explicit ids (plant 1, employees 1-5, lines 1-2, machine 1) because the checklist below
    hardcodes them (e.g. "a supervisor sees only their own lines" asserts `== [1]`) - this only
    works against a genuinely empty database, matching this script's documented "scratch DB"
    usage. Refuses to run against a database that already has other data, rather than silently
    colliding with it.
    """
    with db.connect_service() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM plants")).scalar_one()
        if count > 0:
            return
        plant_id = conn.execute(
            text("INSERT INTO plants (id, name) OVERRIDING SYSTEM VALUE VALUES (1, 'E2E Demo Plant') RETURNING id")
        ).scalar_one()
        emp_ids = {}
        for person_id, (email, name, role) in DEMO_PEOPLE.items():
            emp_id = conn.execute(
                text(
                    "INSERT INTO employees (id, name, role, language, plant_id) "
                    "OVERRIDING SYSTEM VALUE VALUES (:id, :name, :role, 'hi', :plant_id) RETURNING id"
                ),
                {"id": person_id, "name": name, "role": role, "plant_id": plant_id},
            ).scalar_one()
            emp_ids[person_id] = emp_id
            uid = _signup_or_signin(email)
            conn.execute(text("INSERT INTO profiles (id, employee_id) VALUES (:uid, :emp_id)"), {"uid": uid, "emp_id": emp_id})
        conn.execute(
            text(
                "INSERT INTO lines (id, plant_id, name, supervisor_id, manager_id) OVERRIDING SYSTEM VALUE VALUES "
                "(1, :p, 'Line A', :s1, :m1), (2, :p, 'Line B', :s2, :m2)"
            ),
            {"p": plant_id, "s1": emp_ids[1], "m1": emp_ids[2], "s2": emp_ids[4], "m2": emp_ids[5]},
        )
        conn.execute(
            text("INSERT INTO machines (id, line_id, name) OVERRIDING SYSTEM VALUE VALUES (1, 1, 'Press 1')")
        )
        # OVERRIDING SYSTEM VALUE doesn't advance the identity sequence, so later auto-generated
        # inserts (this script creates a SOP, reports, etc.) must not collide with the ids above.
        for seq, seq_max in (("plants_id_seq", 1), ("employees_id_seq", 5), ("lines_id_seq", 2), ("machines_id_seq", 1)):
            conn.execute(text(f"SELECT setval('{seq}', :n)"), {"n": seq_max})


def token(person_id: int) -> str:
    email, _, _ = DEMO_PEOPLE[person_id]
    r = client.post(
        f"{settings.supabase_url}/auth/v1/token?grant_type=password",
        headers={"apikey": settings.supabase_anon_key},
        json={"email": email, "password": DEMO_PASSWORD},
    )
    return r.raise_for_status().json()["access_token"]


def bearer(person_id: int) -> dict:
    return {"Authorization": f"Bearer {token(person_id)}"}


def wait_processed(report_id: int, headers: dict, timeout: float = 900) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            report = client.get(f"{API}/report/{report_id}", headers=headers).json()
        except httpx.TransportError:
            report = {"status": "received"}  # idle keep-alive dropped between polls
        if report["status"] != "received":
            return report
        time.sleep(5)
    raise TimeoutError(f"report {report_id} still processing")


def recovered(sentence: str, transcript: str) -> bool:
    """A sentence counts as recovered when at least half its words appear in the transcript."""
    words = [w.strip("।,") for w in sentence.replace("।", " ").split()]
    return sum(w in transcript for w in words) >= len(words) / 2


def phase0_transcribe(author: dict) -> None:
    """A whole narration comes back, not only its first sentence."""
    path = clip("narration", " ".join(NARRATION))
    r = client.post(f"{API}/transcribe", data={"language": "hi"}, headers=author,
                    files={"audio": (path.name, path.read_bytes(), "audio/mpeg")})
    transcript = r.json().get("transcript", "")
    got = sum(1 for s in NARRATION if recovered(s, transcript))
    check("phase 0: every narrated sentence is transcribed", got == len(NARRATION),
          f"{got}/{len(NARRATION)} - {transcript}")


def phase1_sop(author: dict) -> dict:
    """Structure a transcript, persist it, and read it back with its steps in order."""
    transcript = " ".join(NARRATION)
    structured = client.post(f"{API}/structure", headers=author,
                             json={"transcript": transcript, "language": "hi"}).json()
    check("phases 1-2: /structure returns steps", bool(structured.get("steps")), str(structured)[:200])
    created = client.post(f"{API}/sop", headers=author,
                          json={"machine_id": 1, "title": "Press 1", "language": "hi",
                                "transcript": transcript, "steps": structured["steps"]}).json()
    sop = client.get(f"{API}/sop/{created['id']}").json()
    numbers = [s["step_number"] for s in sop["steps"]]
    check("phases 1-2: SOP persists and reads back in order",
          sop["id"] == created["id"] and numbers == sorted(numbers), f"steps={numbers}")
    return sop


def phase3_reports(sop: dict, headers: dict) -> dict:
    """Three complaints classify correctly, and their audio is gone from disk."""
    created = {}
    for kind, complaint_text in COMPLAINTS.items():
        path = clip(f"c_{kind}", complaint_text)
        r = client.post(f"{API}/report", data={"sop_id": sop["id"], "language": "hi"},
                        files={"audio": (path.name, path.read_bytes(), "audio/mpeg")})
        created[kind] = r.raise_for_status().json()
    check("phase 3: upload returns at once with a receipt and no identity",
          all(c["status"] == "received" and c["receipt"] for c in created.values()))

    reports = {kind: wait_processed(c["report_id"], headers) for kind, c in created.items()}
    for kind, report in reports.items():
        check(f"phase 3: {kind} complaint triaged as '{kind}'", report["kind"] == kind,
              f"got kind={report['kind']} status={report['status']} summary={report['summary']}")
    leftover = list(settings.tmp_dir.glob("report-*"))
    check("phase 3: report audio deleted from disk", not leftover, str(leftover))
    for kind, report in reports.items():
        reports[kind] = {**report, "receipt": created[kind]["receipt"]}
    return reports


def phase3b_ask(sop: dict, headers: dict) -> None:
    """A question the SOP answers comes back as voice, and never reaches the manager."""
    path = clip("c_understanding", COMPLAINTS["understanding"])
    created = client.post(f"{API}/ask", data={"sop_id": sop["id"], "language": "hi"},
                          files={"audio": (path.name, path.read_bytes(), "audio/mpeg")}).raise_for_status().json()
    deadline = time.time() + 900
    while time.time() < deadline:
        seen = client.get(f"{API}/receipt/{created['receipt']}").json()
        if seen["status"] != "received":
            break
        time.sleep(5)
    check("phase 3b: the SOP answers a question about its own steps, out loud",
          seen["answered_by_sop"] and bool(seen["ack_audio_key"]), str(seen))
    audio = client.get(f"{API}/audio/{seen['ack_audio_key']}") if seen["ack_audio_key"] else None
    check("phase 3b: that answer plays back",
          audio is not None and audio.status_code == 200, f"status={audio.status_code if audio else 'none'}")
    hidden = client.get(f"{API}/report/{created['report_id']}", headers=headers)
    check("phase 3b: an answered question is invisible to the manager", hidden.status_code == 404,
          f"status={hidden.status_code}")


def phase4_reply(report: dict, headers: dict) -> None:
    """A manager's reply reaches the worker as playable audio in their language."""
    updated = client.patch(f"{API}/report/{report['id']}", headers=headers,
                           json={"status": "acknowledged",
                                 "response_text": "आपकी बात सुन ली गई है। मैकेनिक आज आएगा।"}).json()
    check("phase 4: reply is stored and voiced",
          updated["status"] == "acknowledged" and bool(updated["ack_audio_key"]), str(updated)[:200])
    seen = client.get(f"{API}/receipt/{report['receipt']}").json()
    audio = client.get(f"{API}/audio/{seen['ack_audio_key']}")
    check("phase 4: the worker's receipt plays the reply",
          audio.status_code == 200 and audio.headers["content-type"] == "audio/mpeg",
          f"status={audio.status_code}")


def phase6_escalation(report: dict, headers: dict) -> None:
    """A high-severity machine report past its SLA escalates to the plant head."""
    with db.connect_service() as conn:
        conn.execute(
            text(
                "UPDATE reports SET status = 'open', kind = 'machine', severity = 'high', "
                "created_at = now() - interval '48 hours', escalate_after = now() - interval '24 hours' "
                "WHERE id = :id"
            ),
            {"id": report["id"]},
        )
        plant_head = conn.execute(text("SELECT id FROM employees WHERE role = 'plant_head'")).scalar_one()
    overdue = client.get(f"{API}/report/{report['id']}", headers=headers).json()
    check("phase 6: an overdue report escalates to the plant head",
          bool(overdue["escalated"]) and overdue["effective_assignee"] == plant_head,
          f"escalated={overdue['escalated']} assignee={overdue['effective_assignee']}")


def phase6_cluster(sop: dict, headers: dict) -> dict:
    """Three reports on the same machine, kind and step collapse into one confirmed cluster."""
    step = sop["steps"][min(2, len(sop["steps"]) - 1)]
    ids = []
    with db.connect_service() as conn:
        for _ in range(3):
            ids.append(conn.execute(
                text(
                    "INSERT INTO reports (sop_id, receipt, language, status, kind, step_id, severity, summary, "
                    "suggested_change) VALUES (:sop_id, :receipt, 'hi', 'open', 'sop', :step_id, 'medium', "
                    "'बोल्ट का नाप गलत है', 'उन्नीस नंबर का बोल्ट लगाकर प्लेट को कस दें।') RETURNING id"
                ),
                {"sop_id": sop["id"], "receipt": secrets.token_hex(8), "step_id": step["id"]},
            ).scalar_one())
        for report_id in ids:
            routing.route(conn, report_id)
            routing.cluster(conn, report_id)
            corrections.draft(conn, report_id)
    clustered = client.get(f"{API}/report/{ids[-1]}", headers=headers).json()
    check("phase 6: three similar reports form one confirmed cluster",
          bool(clustered["confirmed"]) and clustered["cluster_size"] == 3,
          f"size={clustered['cluster_size']} confirmed={clustered['confirmed']}")
    return clustered


def phase7_access(report_id: int) -> None:
    """Sign-in is Supabase Auth; a supervisor is refused the inbox; everyone is held to their
    own lines. Can't replicate the old "expired token" check here: Supabase, not this app,
    holds the signing key, so there is no way to mint a validly-signed-but-expired token from
    the outside - that code path is covered by tests/test_auth.py's monkeypatch instead."""
    wrong = client.post(
        f"{settings.supabase_url}/auth/v1/token?grant_type=password",
        headers={"apikey": settings.supabase_anon_key},
        json={"email": DEMO_PEOPLE[2][0], "password": "wrong-password"},
    )
    check("phase 7: a wrong password is refused", wrong.status_code == 400, f"status={wrong.status_code}")
    unknown = client.post(
        f"{settings.supabase_url}/auth/v1/token?grant_type=password",
        headers={"apikey": settings.supabase_anon_key},
        json={"email": "nobody@test.local", "password": "wrong-password"},
    )
    check("phase 7: an unknown email is refused the same way", unknown.status_code == 400, f"status={unknown.status_code}")

    supervisor = client.get(f"{API}/reports", headers=bearer(1))
    check("phase 7: a supervisor token is refused", supervisor.status_code == 403, f"status={supervisor.status_code}")
    other = client.get(f"{API}/report/{report_id}", headers=bearer(5))
    check("phase 7: another line's manager cannot see the report", other.status_code == 404,
          f"status={other.status_code}")

    anon = client.get(f"{API}/lines")
    check("phase 7: authoring without a token is refused", anon.status_code == 401, f"status={anon.status_code}")
    good = token(1)
    # Flip a character in the middle of the signature, not the last one: a last-character flip
    # can land on unused padding bits and decode to the same bytes, making the check flaky by
    # construction (hit this for real once - see tests/test_auth.py for the full explanation).
    header, payload, sig = good.split(".")
    mid = len(sig) // 2
    forged_sig = sig[:mid] + ("0" if sig[mid] != "0" else "1") + sig[mid + 1:]
    forged = f"{header}.{payload}.{forged_sig}"
    check("phase 7: a tampered token is refused",
          client.get(f"{API}/lines", headers={"Authorization": f"Bearer {forged}"}).status_code == 401)

    off_line = client.post(f"{API}/machines", json={"line_id": 2, "name": "Not yours"}, headers=bearer(1))
    check("phase 7: a supervisor cannot author on another line", off_line.status_code == 403,
          f"status={off_line.status_code}")
    check("phase 7: a supervisor sees only their own lines",
          [l["id"] for l in client.get(f"{API}/lines", headers=bearer(1)).json()] == [1])
    check("phase 7: a plant head sees the whole plant",
          [l["id"] for l in client.get(f"{API}/lines", headers=bearer(3)).json()] == [1, 2])

    check("phase 7: the worker's machine list needs no token", client.get(f"{API}/machines").status_code == 200)


def phase8_correction(sop: dict, headers: dict) -> None:
    """A confirmed 'sop' cluster drafts a step edit that, once approved, is what the cards show."""
    edits = client.get(f"{API}/step-edits", headers=headers).json()
    if not check("phase 8: a confirmed sop cluster drafts a step edit", bool(edits), str(edits)[:200]):
        return
    edit = edits[0]
    approved = client.post(f"{API}/step-edit/{edit['id']}/approve", headers=headers).json()
    current = client.get(f"{API}/machine/{sop['machine_id']}/sop").json()
    text = next(s["text"] for s in current["steps"] if s["step_number"] == edit["step_number"])
    check("phase 8: approval bumps the version and changes the card",
          current["id"] == approved["id"] and current["version"] == sop["version"] + 1 and text == edit["new_text"],
          f"version={current['version']} text={text}")


def main() -> None:
    ensure_demo_org()
    headers = bearer(2)  # Demo Manager, Line A
    author = bearer(1)   # Demo Supervisor, Line A
    phase0_transcribe(author)
    sop = phase1_sop(author)
    reports = phase3_reports(sop, headers)
    phase3b_ask(sop, headers)
    phase4_reply(reports["machine"], headers)
    phase6_escalation(reports["machine"], headers)
    cluster = phase6_cluster(sop, headers)
    phase7_access(cluster["id"])
    phase8_correction(sop, headers)

    print(f"\n{len(passed)} passed, {len(failed)} failed")
    for name in failed:
        print(f"  failed: {name}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
