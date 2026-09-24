# Bolo (worker voice feedback) — build progress

Tracks work against `feature-plan.md`. Last updated 2026-09-24.

## Status

| Phase | What | Status |
|---|---|---|
| 0 | ASR truncation fix | Done, verified: `_WINDOW_SECONDS` is 4 |
| 1 | SQLite persistence and SOP identity | Done, verified |
| 2 | Shared LLM helper | Done, verified |
| 3 | Async voice report ingestion and triage | Done, re-verified after the Phase 0 fix |
| 4 | Manager inbox and voiced reply | Done, verified |
| 5 | Frontend: card mic button and inbox page | Done, tested in Chrome |
| 6 | Routing, escalation, repeat-report clusters | Done, verified |
| 7 | Access control | Done, verified |
| 8 | SOP self-correction | Done, verified |

All of it is committed on the `worker-voice-feedback` branch.

## Done

### Phase 1: Persistence (`app/db.py`, `app/routes/sop.py`)
- stdlib `sqlite3`, no ORM. Tables: `plants`, `people`, `lines`, `machines`, `sops`, `steps`, `reports`, `step_edits`.
- `V2S_DB_PATH` defaults to `tmp_dir/voice-to-sop.db`.
- An empty DB is seeded with a demo org: one plant, Line A and Line B, each with its own supervisor and manager, one plant head, and machines 1 and 2.
- Routes: `POST /api/sop` saves each new SOP as the machine's next version. `GET /api/sop/{id}`, `GET /api/sops`.
- Removed the dead `StepWithAudio` / `SOPWithAudioResponse` schemas.

### Phase 2: LLM helper (`app/llm.py`)
- `call_json(messages, model_cls)`: one LLM call, JSON extraction, validation, and one retry. `structuring.py` now uses it.
- Verified `/api/structure` against the real Groq endpoint.

### Phase 3: Report ingestion (`app/routes/report.py`, `app/triage.py`)
- `POST /api/report` returns 202 at once (about 0.1 s). ASR then triage run as a background task.
- One LLM call both cleans the text into a summary and classifies it (`kind`, `step_id`, `severity`, `suggested_change`). The raw transcript is never stored.
- The audio file is deleted in `finally`, including when processing fails. A failed run sets `status='failed'` and records the error.
- Status flow: `received` -> `open`, or `failed`. Managers can later set `acknowledged` or `resolved`. This departs from the plan's `triaged`, because `open` is the state that escalation checks.
- End-to-end test (live server, 3 spoken clips): all 3 `kind`s correct, all audio removed from disk. **But 2 of the 3 summaries were truncated to their first sentence** (see Phase 0).

### Phase 4: Inbox and reply
- `GET /api/reports?status=&kind=` and `PATCH /api/report/{id}`.
- A reply is voiced by TTS in the report's language and played through the existing `/api/audio/{key}`. Verified with Marathi.
- A report still processing (`received`) or `failed` cannot be replied to (409).

### Phase 5: Frontend (`static_preview/index.html`, `static_preview/inbox.html`)
- Generating a SOP now also saves it. The page takes `?machine=<id>` (current version) or `?sop=<id>`.
- Each card has a hold-to-record mic. It shows सुन लिया गया / ऐकले गेले once the upload succeeds, then polls quietly and shows a reply button when the manager answers.
- Inbox page: sign-in, kind/status filters, escalation and cluster badges, a reply box, and approve/reject cards for drafted step edits.

### Phase 6: Routing and escalation (`app/routing.py`, `report_view` in `db.py`)
- On triage a report is assigned to its line's **manager**, never the supervisor.
- `escalate_after` is 24 h for high-severity machine reports and 72 h otherwise. The plan said only "longer" for the second case; 72 h is my choice.
- Escalation, effective assignee (the plant head once overdue) and cluster size are all computed on read in a SQL view. There is no scheduler.
- Clustering: same machine, kind and step, unresolved, within 30 days. A cluster of 3 or more is `confirmed` and sorts first.

### Phase 7: Access control (`app/auth.py`, `app/routes/login.py`)
- `POST /api/login {person_id, secret}` returns an HMAC-signed token. Role is read from the DB on every request.
- Supervisors get 403. A manager sees only their own lines; the plant head sees the whole plant. Reports outside your scope return 404.
- Report **submission** stays unauthenticated. The worker gets a random `receipt` and polls `GET /api/receipt/{receipt}`, which returns only status and reply audio.
- CORS now uses `V2S_CORS_ORIGINS` (default empty; the preview is same-origin).
- `V2S_AUTH_SECRET` is **required**; the app won't start without it. It is added to the local `.env`, and `render.yaml` sets `generateValue: true`.

### Phase 8: SOP self-correction (`app/corrections.py`)
- A confirmed `sop` cluster drafts one step edit, stored in `step_edits` (never in `sops`, so a draft can't reach the cards).
- Approving creates the machine's next SOP version with the step replaced by `step_number`, keeps the old version, and resolves the cluster's reports.
- `GET /api/machine/{id}/sop` returns the current (highest) version.

## Phase 0 findings

### Sweep (TTS clips with known text)

| Window | Short clip, 23 s, 5 sentences | Long clip, 68 s, 15 sentences |
|---|---|---|
| 4 s | 5/5, WER 0.02 | 15/15, WER 0.01 |
| 5 s | 5/5, WER 0.02 | 15/15, WER 0.01 |
| 6 s | 5/5, WER 0.02 | 14/15, WER 0.14 |
| 8 s | 3/5, WER 0.29 | 10/15, WER 0.53 |
| 10 s | 3/5, WER 0.42 | 8/15, WER 0.50 |
| 15 s | 2/5, WER 0.62 | 5/15, WER 0.68 |
| 25 s (old value) | 1/5, WER 0.79 | 4/15, WER 0.77 |

### Worker complaint clip (`c_machine`, about 10 s, 3 sentences)

| Window | Windows | Sentences recovered |
|---|---|---|
| 25 s | 1 | 1/3 |
| 5 s | 2 | 2/3 (middle sentence dropped) |
| 4 s | 3 | 3/3 |
| 3 s | 3 | 3/3 |

**Conclusion:** the model stops after the first sentence of any window that holds two or more. Short reports are affected too, not only long recordings. 4 s is the largest window that kept every sentence on every clip tested, so `_WINDOW_SECONDS = 4.0`. `_warn_if_truncated` now logs any window whose text runs under 3 characters per second, so the same silent loss would show up in the log next time.

Verified after the fix: `POST /api/transcribe` on a 5-sentence narration returns all five, and the three complaint summaries come back whole instead of as first sentences.

## Verification

`backend/scripts/e2e.py` runs the feature plan's checklist against a live server: 16 checks,
all passing on 2026-09-24 (transcription completeness, structure, persistence, the three-way
triage on spoken clips, audio deletion, the voiced reply, escalation to the plant head,
a confirmed cluster of three, supervisor 403 and cross-line 404, and an approved step edit
changing what the cards show).

Phase 5 was tested in Chrome against the same server: holding a card's mic really records from
the machine's microphone and uploads (confirmation `सुन लिया गया`). To get a report with real
speech in it, a second run replaced `MediaRecorder` with a recorded Hindi complaint and left
the rest of the page path untouched; that report appears in the inbox triaged as machine/high,
a reply from the inbox is voiced and plays back on the card, and approving a drafted card
change from the inbox bumps the SOP version and changes the card text.

## Open issues and decisions

- **Railway:** set `V2S_AUTH_SECRET` in the dashboard, or the deploy fails to start.
- **SQLite on ephemeral disk:** data is lost on every redeploy. Decide on a volume or Postgres before any pilot.
- **4 s windows cost time:** more windows means more ASR passes. A 68 s clip takes about 300 s on this CPU at 4 s versus 77 s at 25 s. Report ingestion is already asynchronous, so this is latency in the background task, not in the worker's confirmation - but it is the price of not losing sentences.
- **Severity over-flagging:** the bolt-size report came back `high`, the same tendency the plan notes for the structuring prompt.
- **Tokens never expire.** Missing token returns 403 (FastAPI `HTTPBearer` default); a bad token returns 401.
- **Local only:** Hugging Face downloads on this machine need `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` pointed at `backend/.venv/windows-roots.pem`. No code change is needed.
- **Schema changes:** delete the dev DB after schema changes. `CREATE TABLE IF NOT EXISTS` does not add new columns to an existing file.
- A manager rejecting a drafted step edit ends that cluster's drafting. New reports only start a new cluster after the old one is resolved.
