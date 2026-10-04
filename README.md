# Vernacular Voice-to-SOP

![CI](https://github.com/Atharva0222/vernacular-voice-to-sop/actions/workflows/ci.yml/badge.svg)

A plant-floor CRM built on Supabase. Voice-to-SOP is its original feature: a supervisor
narrates a procedure in Hindi or Marathi, the system turns it into simple picture-and-voice SOP
cards for the workers on that machine, and workers can hold a mic button on any card to report
a problem in their own language — triaged into **machine**, **sop** or **understanding**,
routed to the line's manager (never the supervisor), and answered back as voice on the card.
Alongside it: **Employee management** (a plant-wide directory, including line workers tracked
by name for scheduling purposes), **Workforce management** (shift definitions, assignments, and
supervisor-operated clock-in/out), and **HR management** (self-service leave with approval, and
a minimal recruitment pipeline with resume storage).

Workers never have an account, in any module — that's structural, not a gap (see `CLAUDE.md`'s
Auth section). Staff sign in with Supabase Auth and everything is scoped by role and by which
plant/line they run, enforced both in the API and via Postgres Row Level Security.

`TESTING.md` walks through the voice-to-SOP loop by hand. `docs/` holds historical planning
docs from before the CRM expansion - not kept in sync, see `CLAUDE.md`.

## Pipeline

1. **ASR** — fine-tuned Whisper per language (`vasista22/whisper-hindi-medium`,
   `steja/whisper-small-marathi`), run over silence-split windows.
2. **Structuring** — an OpenAI-compatible LLM turns the transcript into numbered steps with
   a safety flag and an icon.
3. **TTS** — edge-tts reads each card back in the worker's language.

## Run locally

Needs a Supabase project - either a cloud one you already have, or for local dev with no cloud
account, the Supabase CLI's own stack (`supabase start`, requires Docker):

```bash
cd backend
supabase init && supabase start   # prints local URLs/keys; `supabase status` reprints them later
```

Already on a cloud project? Skip the block above - just put that project's values straight into
`.env` below (Project Settings → API / Database on the Supabase dashboard) and run everything
else exactly the same way, no Docker required. The one exception is `pytest` (see
Development below), which still wants the local CLI stack since it truncates and reseeds a demo
org on every run.

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # then set the Supabase values (supabase status, or your cloud project's dashboard) and your LLM key
alembic upgrade head        # schema is Alembic-managed - nothing seeds it on boot, see below
cd frontend && cp .env.example .env   # set VITE_SUPABASE_URL/VITE_SUPABASE_ANON_KEY
npm install && npm run build && cd ..   # one-time, rebuild after editing frontend/
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Open `http://localhost:8001/preview/`. **Workers do not sign in, in any module**: the worker
door leads straight to the machine list, that machine's cards, and one speak button that the
SOP answers when it can. **Staff sign in with Supabase Auth** (email + password), and their role
in `employees` decides the screen and what they can reach: supervisors add machines and record
procedures for their own lines, managers get the report inbox, HR/recruiting roles get the HR
tab, and the Employees/Workforce tabs are scoped to the lines or plant each role actually runs.
There's no seeded demo org out of the box; `scripts/e2e.py` creates one (and the matching
Supabase Auth users) the first time it runs against an empty project. Models download on first
transcription.

The UI (`backend/frontend/`) is a Vite + React + TypeScript + Tailwind app; FastAPI serves its
built output as static files at `/preview`, so it needs a `npm run build` after any frontend
change (`uvicorn --reload` only watches `app/`, not `frontend/`). For active frontend
development with hot reload, run `cd backend/frontend && npm run dev` instead — its dev server
proxies `/api` to the backend on port 8001, so both can run side by side.

Docker: `docker build -t voice-to-sop backend --build-arg VITE_SUPABASE_URL=... --build-arg
VITE_SUPABASE_ANON_KEY=... && docker run --env-file backend/.env -p 8000:8000 voice-to-sop`
(the build args are needed because Vite inlines them into the bundle at build time, not
runtime - see `backend/Dockerfile`). Running without Docker, `backend/.env` can still carry
those same `VITE_SUPABASE_*` keys harmlessly - `app/config.py`'s `Settings` sets `extra =
"ignore"` so pydantic-settings doesn't choke on them when it reads `.env` directly.

## Development

```bash
cd backend
pip install -r requirements-dev.txt   # adds pytest, ruff on top of requirements.txt
ruff check app tests                  # lint
pytest                                # needs `supabase start` running; truncates+reseeds a fixed demo org per test
```

CI (`.github/workflows/ci.yml`) runs both on every push/PR. The `docker-build` job is manual
(`workflow_dispatch`) rather than automatic: the image's build step bakes the Whisper
checkpoints in from Hugging Face (see `backend/Dockerfile`), and any `app/` change busts that
layer's cache, so running it on every push would re-pull several GB each time.

**Migrations.** `backend/migrations/` is Alembic-managed; every revision is hand-written Postgres
DDL (including RLS policies - autogenerate never produces those). Schema is **not** auto-created
on boot: a hosted Supabase project is shared, not a per-dev scratch file, so `alembic upgrade
head` is a required, explicit step, both locally and as the first thing the Docker image's `CMD`
does on every deploy.

```bash
cd backend
alembic upgrade head      # apply pending migrations, targets V2S_DATABASE_MIGRATE_URL
alembic revision -m "..." # scaffold a new migration for a future schema change
```

## Settings

All read from the environment or `backend/.env`, prefix `V2S_`.

| Variable | Default | What it does |
|---|---|---|
| `V2S_DATABASE_URL` | *required* | Supabase Postgres connection - the Supavisor **session-mode** pooler for a deployed project (transaction-mode pooling breaks psycopg3's prepared-statement cache), or the direct `postgresql://postgres:postgres@127.0.0.1:54322/postgres` for local `supabase start`. |
| `V2S_DATABASE_MIGRATE_URL` | = `V2S_DATABASE_URL` | Direct (unpooled) connection Alembic uses for DDL. Only needs to differ from the above against a deployed project with a pooler in front. |
| `V2S_SUPABASE_URL` / `V2S_SUPABASE_ANON_KEY` | *required* | Supabase project URL and publishable/anon key. No JWT secret setting exists: `current_person()` verifies staff tokens against Supabase's public JWKS instead (current Supabase projects sign with a per-project key, not a shared secret). |
| `V2S_SUPABASE_SERVICE_ROLE_KEY` | *required* | RLS-bypassing - server-only, never sent to the frontend. Used by the worker-facing routes and the recruitment module's resume-upload signing. |
| `V2S_CORS_ORIGINS` | *empty* | Allowed browser origins. The bundled preview is same-origin and needs none. |
| `V2S_LLM_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible endpoint (Ollama locally, Groq in deployment). |
| `V2S_LLM_MODEL` / `V2S_LLM_API_KEY` | `llama3.2:3b` / `ollama` | Model and key for that endpoint. |
| `V2S_ASR_MODEL_HI` / `V2S_ASR_MODEL_MR` / `V2S_ASR_DEVICE` | see `app/config.py` | ASR checkpoints and device (`auto`/`cpu`/`cuda`/`mps`). |
| `V2S_TTS_VOICE_HI` / `V2S_TTS_VOICE_MR` | edge-tts voices | Playback voices. |
| `V2S_TMP_DIR` | system temp `/voice-to-sop` | Uploads, audio cache and the default DB location. |

## API

**Open (no token).** The worker's path. A worker has no account, so none of this asks for one.

| Route | Purpose |
|---|---|
| `GET /api/machines`, `GET /api/machine/{id}/sop` | the machine picker, and that machine's current (highest) version |
| `GET /api/sop/{id}` | read one SOP |
| `POST /api/tts`, `GET /api/audio/{key}` | synthesize and play audio |
| `POST /api/report`, `POST /api/ask` | a worker's voice report; returns `202` at once with a receipt |
| `GET /api/receipt/{receipt}` | the worker's own view: status and reply audio only |
| `GET /api/health` | health check |

**Sign in** via Supabase Auth directly from the frontend (`supabase.auth.signInWithPassword`),
not through this API - there is no `POST /api/login`. Every other route below expects
`Authorization: Bearer <supabase access token>`; `current_person()` re-verifies it (signature +
expiry, against Supabase's public JWKS) on every request and reads role/plant/line live from
`employees`, so a role change applies immediately with no re-login needed. `GET /api/me` returns
the caller's own `{name, role}` once signed in.

**Authoring token** (any signed-in staff member, held to the lines they run: a supervisor or
manager to their own, a plant head to their whole plant). Off-line writes get `403`.

| Route | Purpose |
|---|---|
| `POST /api/transcribe` | audio -> transcript |
| `POST /api/structure` | transcript -> steps (pure, stores nothing) |
| `POST /api/sop` | persist an SOP as the next version for its machine |
| `GET /api/sops` | every SOP on the caller's own lines |
| `POST /api/machines`, `GET /api/lines` | add a machine; the lines the caller may use |
| `GET /api/shift-assignments`, `POST /api/shift-assignments` | the roster for the caller's own lines (or whole plant for a plant head); assign a shift |
| `POST /api/attendance/clock-in`, `.../{id}/clock-out` | kiosk-style: a supervisor clocks a named worker in/out on a shared device |

**Manager token.** Supervisors (and HR/recruiting roles) get `403`; a manager sees only their
own lines, a plant head their whole plant.

| Route | Purpose |
|---|---|
| `GET /api/reports?status=&kind=` | inbox, confirmed clusters first |
| `GET /api/report/{id}`, `PATCH /api/report/{id}` | read one; set status or reply (voiced by TTS) |
| `GET /api/step-edits?status=` | card changes drafted from confirmed reports |
| `POST /api/step-edit/{id}/approve`, `.../reject` | approve writes the next SOP version |

**Any staff token.** Plant-wide, read-only unless noted.

| Route | Purpose |
|---|---|
| `GET /api/employees?department_id=&employment_status=` | the plant's directory, including `role='worker'` rows tracked for scheduling only (no account, ever) |
| `GET /api/departments`, `GET /api/shifts` | department and shift-definition lists |
| `GET /api/leave-types`, `GET /api/leave-balances`, `GET /api/leave-requests` | leave reference data and the caller's own balance/requests (hr_admin/plant_head see everyone's in their plant) |
| `POST /api/leave-requests` | self-service leave request (always for the caller themselves) |

**hr_admin / plant_head token** (`org_admin`): `POST`/`PATCH /api/employees`, `POST
/api/departments`, `POST /api/shifts`, `POST /api/leave-balances` (upsert), `POST
/api/leave-requests/{id}/approve`/`.../reject` (deducts the balance on approve). `leave-types`
creation is hr_admin only, not plant_head.

**hr_admin / recruiter / plant_head token** (`recruiter_access`), scoped org-wide rather than
per-plant: `GET`/`POST /api/job-postings`, `GET`/`POST /api/candidates`, `POST
/api/candidates/{id}/resume-upload-url` (a short-lived Supabase Storage signed URL the browser
uploads directly to) + `PATCH /api/candidates/{id}` (records the resulting path), `GET`/`POST
/api/applications`, `PATCH /api/applications/{id}` (stage transitions).

## Observability

Every request gets a `X-Request-ID` response header and one structured (JSON) log line with
method, path, status and duration. `GET /metrics` exposes Prometheus-format counters and a
latency histogram, labeled by route template (not raw path, so `/api/sop/{id}` stays one series
regardless of id). `POST /api/report`, `POST /api/ask` are capped at 20/minute per client; `POST
/api/transcribe`, `POST /api/tts` at 30/minute — all in-memory and per-process, so a
multi-worker deployment would need a shared backend (e.g. Redis) for the limit to hold across
processes. Staff sign-in is rate-limited by Supabase itself, not this app.

## Privacy

No worker identity is captured anywhere. Report audio is deleted as soon as it is
transcribed and is never fetchable, so a voice cannot be recognised; only cleaned text is
kept. Reports are routed to the line's manager and are invisible to supervisors. On a small
line a manager may still guess who spoke from the content — the design reduces that risk, it
does not remove it.

## Verification

`python scripts/e2e.py` runs the plan's checklist against a running server: transcription
completeness, persistence, the three-way triage, the voiced reply, escalation, clustering,
access control and SOP self-correction. Seeds its own demo org (and matching Supabase Auth
users) on first run against an empty project - safe to rerun, but only seeds against a
genuinely empty `plants` table, matching its "scratch DB" assumption.

## Known limits

- Escalation is computed on read, so nothing escalates until a manager opens the inbox.
- Triage accuracy is unmeasured, and Marathi ASR is weaker than Hindi.
- Payroll is explicitly out of scope for the HR module - leave and a minimal recruitment
  pipeline only. The schema leaves room (`employees`, `attendance`, `leave_balances`) for it
  to be added later without rework.
- Recruitment (`job_postings`/`candidates`/`applications`) is scoped org-wide to
  hr_admin/recruiter/plant_head, not filtered per plant - fine for a single-plant deployment,
  a real gap for a genuinely multi-plant org with separate recruiting teams.
- Leave is self-service for staff with an account (supervisor and up); `role='worker'` rows
  have no account, so workforce-tracked line workers can't request leave through this yet.
- Leave balances don't auto-accrue; hr_admin sets them directly. No payroll-grade accrual
  engine exists.
