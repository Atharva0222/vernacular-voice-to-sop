# Feature Plan — Worker Voice Feedback ("Bolo")

## Context

`feature.md` specifies a return channel for the SOP cards. Today the product is one-way:
a supervisor narrates, cards are generated, and nothing ever flows back. The worker at the
machine — the first person to see a loose pedal or a wrong bolt size — has no way to report
it, because every existing channel requires writing, usually in English, and goes through
the supervisor who is judged on having few problems.

The feature lets a worker hold a mic button, speak in Hindi or Marathi, and have the system
work out whether the **machine**, the **card**, or the **training** is the problem, route it
past the supervisor, and tell the worker they were heard.

The backend cannot support any of this yet. It is a stateless, unauthenticated, three-endpoint
transform service (~400 LOC). There is no database, no identity, no background jobs, no
logging, and no domain entities. Cards are not even addressable — `SOPResponse` has no id, and
`step_number` is an LLM-generated ordinal, not a stable key. A report has nothing to attach to.

## Scope

The **whole ecosystem**, phased for delivery but complete: voice reporting, SOP-grounded
triage, routing past the supervisor, escalation, repeat-report confirmation, manager inbox,
and the reply back to the worker. The existing manager → card pipeline is unchanged; this
adds the return path on top of it.

**Out of scope:** the phone/IVR path described in `feature.md`. Reporting is through the app
or website only, so no telephony provider is needed.

**Assumptions (override either):**

1. **No worker identity is captured at all.** Anonymity becomes true by construction rather
   than by policy, and we avoid building fake security on a system with no auth.
2. **The ASR truncation bug is fixed first**, because every voice report would otherwise be
   silently mangled.

## Blockers found by running the system (not from reading code)

**1. ASR silently drops most of a recording.** `app/asr.py:47` sets `_WINDOW_SECONDS = 25.0`.
A 19.3 s clip collapses to a single 18.1 s window, and these fine-tunes — trained on short
utterance clips — stop generating after roughly the first sentence. Measured on `test_hi.mp3`:

| Window | Windows | Sentences recovered |
|---|---|---|
| 25 s (current) | 1 | 1 of 5 |
| 8 s | 3 | 4 of 5 |
| 5 s | 5 | 5 of 5 |

At 8 s the dropped sentence was the safety warning. Worker reports are exactly this length,
so triage would routinely classify a fragment.

**2. ASR takes ~87 s for a 19 s clip on CPU.** Report ingestion cannot be synchronous.

**3. Disk is ephemeral in production.** Neither `render.yaml` nor `backend/railway.json`
declares a volume, so a SQLite file would be destroyed on every redeploy. Fine for local and
demo; flagged below as a deployment decision.

**4. No auth, CORS is `allow_origins=["*"]`** (`app/main.py:11-16`). Routing "past the
supervisor" is enforceable only by not capturing identity.

## What exists to reuse

- `asr.transcribe(path, language_hint) -> (text, lang)` — `app/asr.py:127`
- `tts.synthesize(text, language) -> (key, path)` — `app/tts.py:18`, served by
  `GET /api/audio/{key}` — `app/routes/tts.py:18`
- Upload → temp file → `finally: unlink` pattern — `app/routes/transcribe.py:26-35`
- Sync `def` route to get threadpool dispatch for CPU work — `app/routes/transcribe.py:17-22`
- `Settings` with `V2S_` prefix — `app/config.py`
- LLM call + fenced-JSON extraction + one retry — `app/structuring.py:30-74` (private; extract)
- `StepWithAudio` / `SOPWithAudioResponse` — `app/schemas.py:38-45` are **dead code**, unused
  by any route. Repurpose or delete.

---

## Phase 0 — Fix the ASR truncation blocker

**Files:** `app/asr.py`

Sweep `_WINDOW_SECONDS` over {4, 5, 6, 8, 10, 15, 25} against `test_hi.mp3` plus at least one
60 s+ clip, scoring recovered-sentence count and total WER. Set the constant from the result;
do not guess. Keep the silence-boundary logic — it is correct, the threshold is not.

Add a cheap guard: if a window yields text whose duration-to-character ratio implies heavy
truncation, log it. Silent data loss is the actual defect.

**Verify:** `POST /api/transcribe` with `test_hi.mp3` returns all five sentences.

## Phase 1 — Persistence and SOP identity

**New:** `app/db.py` — `sqlite3` from stdlib, no ORM (the repo has no DB deps and does not
need one).

Tables: `plants`, `lines`, `people`, `machines`, `sops`, `steps`, `reports`.

The org tables are what make "route past the supervisor" real rather than aspirational:
`machines` belongs to a `line`; a `line` has a `supervisor_id` and a `manager_id`, both
pointing at `people (id, name, role, phone, language)` where role is
`supervisor | manager | plant_head`. A report on a machine resolves to its line, and is routed
to that line's **manager**, never its supervisor. `plant_head` is the escalation target.

Note `people` holds supervisors and managers only — **workers are never recorded**, which is
what keeps reports anonymous.

`sops` gets `machine_id`, `title`, `language`, `transcript`, `version`, `created_at`.
`steps` gets a real surrogate `id` plus `sop_id` and `step_number`, so a report can point at a
specific step that survives re-generation.

**New setting:** `V2S_DB_PATH`, defaulting under `settings.tmp_dir`.

**New routes** in `app/routes/sop.py`: `POST /api/sop` (persist a generated SOP),
`GET /api/sop/{id}`, `GET /api/sops`.

Leave `POST /api/structure` untouched and pure — persistence is a separate, explicit step.

**Verify:** generate an SOP, persist it, fetch it back by id with steps in order.

## Phase 2 — Extract a shared LLM helper

**New:** `app/llm.py` — move `_call_llm`, `_extract_json`, and the validate-then-retry loop out
of `structuring.py` into `call_json(messages, model_cls)`. Refactor `structuring.py` to use it.
Triage needs exactly this behaviour; duplicating it is how the two prompts drift apart.

**Verify:** `POST /api/structure` behaves identically to before the refactor.

## Phase 3 — Voice report ingestion (asynchronous)

**New:** `app/routes/report.py`, `app/triage.py`

`POST /api/report` — multipart: `audio`, `sop_id`, optional `step_id`, `language`.
Writes the audio to a temp path, inserts a `reports` row with `status='received'`, and returns
`{report_id, status}` **immediately**. Processing runs in FastAPI `BackgroundTasks` (adequate
here; a real queue is Phase 6).

Background worker: `asr.transcribe` → clean into a plain paragraph → triage against that SOP's
steps → update the row to `status='triaged'`.

**Triage prompt** (`app/triage.py`) receives the SOP's steps and the report text, returns
strict JSON validated by a Pydantic model:

```
{ "kind": "machine" | "sop" | "understanding",
  "summary": str,            # cleaned, in the worker's language
  "step_id": int | null,     # which step it concerns
  "severity": "low"|"medium"|"high",
  "suggested_change": str | null }
```

`kind` is the heart of the feature and the thing a generic voice-reporting app cannot do,
because it requires the SOP as context.

**Privacy, per `feature.md`:** delete the audio file once transcription succeeds. The recording
never becomes fetchable, so a supervisor can never recognise a voice. Only cleaned text is
stored. No worker identifier is recorded anywhere.

`GET /api/report/{id}` — status polling for the UI.

**Verify:** post a Hindi complaint clip against a stored SOP; poll until `triaged`; confirm the
`kind` is right for each of three hand-made clips (loose pedal → machine; wrong bolt size →
sop; wrong order → understanding); confirm the audio file is gone from disk.

## Phase 4 — Manager inbox and acknowledgement

**Extend:** `app/routes/report.py`

- `GET /api/reports?status=&kind=` — inbox, newest first, text only.
- `PATCH /api/report/{id}` — set `status` (`open`/`acknowledged`/`resolved`) and
  `response_text`.
- On response, call `tts.synthesize(response_text, report.language)` and store the returned
  key as `ack_audio_key`. The worker plays it via the existing `GET /api/audio/{key}`.

**Verify:** acknowledge a report, then fetch and play the ack audio in the worker's language.

## Phase 5 — Frontend

**Files:** `backend/static_preview/index.html`, new `backend/static_preview/inbox.html`

Add a **mic button to each card**, mirroring the existing speaker button — hold to record,
release to send, then a clear "सुन लिया गया / ऐकले गेले" confirmation. The worker must never wait
on the ~87 s pipeline; confirm on upload, not on triage.

`inbox.html`: a minimal manager list with kind/severity/summary and a reply box.

**Verify:** record a complaint in the browser, see it appear in the inbox correctly classified,
reply, and hear the acknowledgement back on the card.

## Phase 6 — Routing, escalation, and repeat-report confirmation

**Files:** `app/routing.py`, extend `app/routes/report.py`

**Routing.** On triage, resolve `machine → line → manager` and stamp `assigned_to` on the
report. The line's supervisor is never an assignee and never appears in any inbox query.

**Escalation without a scheduler.** Do not add a cron or task queue for this. Store
`escalate_after` (a timestamp: `created_at + SLA`, where SLA is 24 h for
`kind='machine' AND severity='high'`, longer otherwise) and compute overdue state on read:
a report whose `escalate_after` has passed and whose status is still `open` is returned as
escalated, and its effective assignee becomes the `plant_head`. This is one indexed column
and a `WHERE` clause instead of a scheduler, and it cannot silently stop running — which is
the failure mode that would quietly break the guarantee `feature.md` makes.

**Repeat-report confirmation.** When a new report is triaged, look for open reports on the
same `machine_id` with the same `kind`, and compare summaries. Start with the cheap version:
same machine + same kind + same `step_id` within 30 days → link them. Add text similarity only
if the cheap version misses too much. Linked reports share a `cluster_id`; a cluster of three
or more is marked `confirmed` and sorts to the top of the inbox.

**Verify:** a high-severity machine report backdated past its SLA appears as escalated and
assigned to the plant head; three similar reports on one machine collapse into one confirmed
cluster.

## Phase 7 — Access control

**Files:** `app/auth.py`, `app/main.py`

The inbox contains worker complaints about named machines and lines. Until there is auth,
anyone who can reach the API can read all of it, and the "hidden from the supervisor" promise
is unenforced. Add the minimum that makes the promise real:

- A signed token per manager (`people.id` + role), issued by a simple login against a
  server-side secret. No user-facing password system yet.
- A `Depends()` guard on every `/api/report*` route resolving the caller to a `people` row.
- Inbox queries filtered to the caller's own lines; a `supervisor` role receives 403 on the
  report routes entirely.
- Tighten `allow_origins` in `app/main.py:11-16` from `["*"]` to the deployed origins.

Report **submission** stays unauthenticated — a worker must be able to speak without an
account, and requiring one would both deter reporting and destroy anonymity.

**Verify:** a supervisor token is refused; a manager token sees only their own lines' reports.

## Phase 8 — SOP self-correction

**Files:** extend `app/routes/sop.py`

This closes the loop and is what makes the cards improve rather than decay. When a `sop`-kind
cluster is confirmed, use the stored `suggested_change` to draft a new version of that step,
and surface it to the manager as an approve/reject diff. Approval writes a new `sops` row with
`version + 1` and re-points the machine at it; the old version is retained for audit.

**Verify:** three reports saying the bolt is 17 mm produce a drafted step edit that, once
approved, is what the cards then show.

---

## Honest limitations to carry into the plan

- **SQLite on ephemeral disk** means data is lost on redeploy. Local/demo is fine; production
  needs a mounted volume or Postgres. Decide before any pilot.
- **Anonymity has a floor that no code can raise.** Phases 3 and 7 remove the audio, capture no
  worker identity, and keep supervisors out of the inbox. But as `feature.md` already admits, on
  a three-person line a manager can often guess who spoke from the content alone. The feature
  reduces the risk; it does not remove it, and it should not be sold as if it does.
- **Escalation only fires when someone reads the inbox**, because it is computed on read rather
  than pushed. If no manager opens the app for a week, nothing escalates. Adding real
  notifications (email/WhatsApp) is the honest fix and is not in this plan.
- **Triage accuracy is unmeasured.** It needs a small labelled set of real worker complaints
  before anyone trusts the three-way split. Note the existing over-flagging tendency: on my test
  narration the structuring prompt marked 4 of 6 steps as safety warnings, including "check if
  the belt is loose", which is not one.
- **Marathi ASR is weaker than Hindi**, and code-mixed factory speech weaker still.

## End-to-end verification

1. `docker build -t voice-to-sop . && docker run -d --env-file .env -p 8000:8000 voice-to-sop`
2. Phase 0: `POST /api/transcribe` with `test_hi.mp3` → all five sentences.
3. Phases 1–2: generate → persist → `GET /api/sop/{id}`.
4. Phase 3: post three complaint clips → correct `kind` on each → audio deleted from disk.
5. Phase 4: acknowledge → ack audio plays in the worker's language.
6. Phase 5: full loop in the browser at `/preview`.
7. Phase 6: backdated high-severity machine report shows as escalated to the plant head; three
   similar reports collapse into one confirmed cluster.
8. Phase 7: supervisor token gets 403; manager token sees only their own lines.
9. Phase 8: a confirmed `sop` cluster drafts a step edit; approving it bumps the SOP version and
   changes what the cards render.
