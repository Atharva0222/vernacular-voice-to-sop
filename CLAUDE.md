# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A supervisor narrates a procedure in Hindi or Marathi; the system turns it into picture-and-voice
SOP cards for workers at that machine. Workers hold a mic button on any card to report a problem
or ask a question in their own language; reports are triaged (machine fault / wrong card / needs
training), routed to the line's manager, and a confirmed cluster of reports can self-correct the
SOP card pending a manager's approval. `TESTING.md` is the full hand-walkthrough of this loop.

## Repository layout

Everything deployable lives under `backend/` — **including the frontend**, at
`backend/frontend/`. This is deliberate, not accidental nesting: Render (`render.yaml`) and
Railway (`backend/railway.json`) both treat `backend/` as the Docker build root, so keeping the
frontend there means it ships in the same image with zero deploy-config changes. Don't move it
back out to a sibling `frontend/` without updating both platforms' configs.

- `backend/app/` — FastAPI backend (Python)
- `backend/frontend/` — React/Vite/TypeScript UI, built to `frontend/dist/` and served by FastAPI
  as static files at `/preview` (see "Frontend serving" below)
- `backend/migrations/` — Alembic migrations (see "Database" below)
- `backend/tests/` — pytest suite
- `backend/scripts/` — `e2e.py` (API checklist), `run_test.ps1` (Windows one-command test
  runner), `sample_sop.py`, `hi_multistep.mp3` (sample Hindi audio for manual testing)
- `docs/` — historical planning docs (`auth-plan.md`, `feature-plan.md`, `feature.md`); these
  describe decisions as they were made and are not kept in sync with later refactors

## Commands

### Backend (run from `backend/`)

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt  # adds pytest, ruff
cp .env.example .env                 # then set V2S_AUTH_SECRET and an LLM key
uvicorn app.main:app --reload --port 8001

pytest                                # full suite, isolated temp SQLite per test, no network/model calls
pytest tests/test_routing.py::test_route_assigns_lines_manager_not_supervisor  # single test
ruff check app tests                  # lint

alembic upgrade head                  # apply pending schema migrations (targets V2S_DB_PATH)
alembic revision -m "..."              # scaffold a new migration
```

### Frontend (run from `backend/frontend/`)

```bash
npm install
npm run dev      # Vite dev server with HMR; proxies /api to the backend on :8001
npm run build    # tsc -b && vite build -> dist/ (uvicorn --reload does NOT rebuild this on change)
npm run lint      # oxlint
```

After any frontend change, the backend won't see it until `npm run build` runs again — `uvicorn
--reload` only watches `app/`, not `frontend/`.

### Docker

```bash
docker build -t voice-to-sop backend
docker run --env-file backend/.env -p 8000:8000 voice-to-sop
```

Two-stage build: a `node` stage runs `npm ci && npm run build` for the frontend, then its
`dist/` is copied into the `python` stage. The Python stage also bakes the Whisper model
checkpoints in at build time (see Dockerfile) so cold starts don't hit Hugging Face — this makes
`app/` changes bust a large layer-cache, so CI only runs the Docker build manually
(`workflow_dispatch`), not on every push.

## Architecture

### Request pipeline

ASR (fine-tuned Whisper per language, lazy-loaded and cached on first use, run over
silence-split windows) → LLM structuring (any OpenAI-compatible chat endpoint — Groq in
deployment, Ollama locally by default) → TTS (edge-tts). `app/asr.py`, `app/structuring.py`,
`app/tts.py`, `app/llm.py`.

### Auth (`app/auth.py`)

No account system. Staff (supervisor/manager/plant_head) sign in with `person_id` + PIN
(scrypt-hashed); the response is an HMAC-signed `id.expiry.signature` token, not a session
lookup — `current_person()` re-verifies the signature and expiry on every request and reads the
role live from the DB, so a role change applies immediately without a new login. Workers have no
account at all; worker-facing routes are deliberately unauthenticated (`/api/report`, `/api/ask`,
`/api/receipt/{receipt}`, `/api/machines`, `/api/machine/{id}/sop`) — this is intentional, not an
oversight, so reporting a problem never requires identifying yourself.

Authorization is scope-based, not role-based alone: `auth.scope_sql()` / `auth.author_scope_sql()`
build a `WHERE line_id IN (...)` clause limiting a manager/supervisor to the lines they run and a
plant_head to their whole plant — always filter through these rather than trusting role name
alone when adding a route.

### Database (`app/db.py` + `migrations/`)

Raw `sqlite3`, no ORM. Two parallel, intentionally non-conflicting paths to the same schema:

- `db.init()` — idempotent `CREATE TABLE/VIEW IF NOT EXISTS` + demo-org seeding, runs on every
  app startup (`main.py` lifespan). This is what local dev and tests rely on.
- `migrations/versions/0001_initial_schema.py` — Alembic, imports `app.db.SCHEMA` directly
  (not copied) so the two can never drift. This is the versioned path for *future* schema
  changes — write new changes as Alembic revisions, not by editing `SCHEMA` and relying on
  `db.init()` alone, since `db.init()` never alters existing tables, only creates missing ones.

The schema is SQLite-specific: `report_view` / `step_edit_view` (the escalation-after-SLA and
worker-report clustering logic) use `strftime()` and boolean-valued computed columns. Porting to
Postgres means rewriting those views for the new dialect, not just changing the connection
string.

### Worker report lifecycle (`app/routing.py`, `app/corrections.py`, `app/routes/report.py`)

A report is triaged into `kind` (machine/sop/understanding) + `severity`, then `routing.route()`
assigns it to the line's manager with an SLA deadline (24h if machine+high severity, else 72h),
and `routing.cluster()` links it to any other open report on the same machine/kind/step within a
30-day window. Once a cluster reaches 3 reports on kind `sop`, `corrections.draft()` proposes a
step-text edit; a manager approving it in the Inbox writes the next SOP version. Worker reports
never store audio — only the transcribed, triaged text.

### Observability (`app/observability.py`, `app/metrics.py`, `app/logging_config.py`)

Structured JSON logs (one line per request: method/path/status/duration/request_id) and
Prometheus counters at `/metrics`, both wired as the *outermost* middleware layer so rate-limit
rejections and CORS failures are still logged/counted. Rate limits (`app/limiter.py`, slowapi)
are in-memory per-process — a multi-worker deployment would need a shared backend (Redis) for
them to hold across processes.

### Frontend serving

The React app is a SPA using `HashRouter` (`#/machines`, `#/cards?machine=1`, etc.) specifically
so FastAPI can serve it as plain static files with no catch-all server route needed — every
client-side path lives after the `#` and never reaches the server. `main.py` mounts
`frontend/dist` at `/preview` only if that directory exists; if it's missing (frontend never
built), it logs a warning and skips the mount rather than failing — `StaticFiles` raises at
*import time* if its directory is absent, which would otherwise take every `/api/*` route down
with it. Keep this guard if touching that mount; pure-backend work (pytest, API-only dev)
shouldn't require Node/npm to be installed.

Framer Motion gotcha worth knowing before it costs you an hour again: a `motion.form` or
`motion.button` with an `exit` prop, rendered inside `AnimatePresence`, can silently swallow the
native click→submit default action after an interrupted animation — the synthetic `onClick`
fires but the browser's form submission doesn't. Keep the real `<form>`/`<button>` as plain
elements and use `motion.div` only as the animating wrapper around them.

### Testing conventions (`backend/tests/`)

`conftest.py`'s `client` fixture points `settings.db_path` at a fresh `tmp_path` file per test
and resets the rate limiter's in-memory store (`limiter.reset()`) before each test — both are
process-wide singletons that leak across tests otherwise. No test hits the network or loads an
ML model; `app.llm.call_json` and `app.asr`/ASR calls are monkeypatched where exercised, and
`triage`/`routing` have direct unit tests against a raw `sqlite3.Connection`.
