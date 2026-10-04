# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A plant-floor CRM built on Supabase. Its original feature, voice-to-SOP: a supervisor narrates
a procedure in Hindi or Marathi; the system turns it into picture-and-voice SOP cards for
workers at that machine. Workers hold a mic button on any card to report a problem or ask a
question in their own language; reports are triaged (machine fault / wrong card / needs
training), routed to the line's manager, and a confirmed cluster of reports can self-correct the
SOP card pending a manager's approval. `TESTING.md` is the full hand-walkthrough of that loop.

Alongside it: **Employee management** (a plant-wide directory, including line workers tracked by
name for scheduling - see the Auth section on what that does and doesn't change), **Workforce
management** (shift definitions, assignments, and supervisor-operated clock-in/out), and **HR
management** (self-service leave with approval, and a minimal recruitment pipeline backed by
Supabase Storage for resumes). All three reuse the same org structure (`plants`/`lines`) and
authorization shapes (`scope_sql`/`author_scope_sql`/`may_author_line`) the original feature
already established - see Architecture below before adding a fourth module from scratch.

## Repository layout

Everything deployable lives under `backend/` — **including the frontend**, at
`backend/frontend/`. This is deliberate, not accidental nesting: Render (`render.yaml`) and
Railway (`backend/railway.json`) both treat `backend/` as the Docker build root, so keeping the
frontend there means it ships in the same image with zero deploy-config changes. Don't move it
back out to a sibling `frontend/` without updating both platforms' configs.

- `backend/app/` — FastAPI backend (Python)
- `backend/frontend/` — React/Vite/TypeScript UI, built to `frontend/dist/` and served by FastAPI
  as static files at `/preview` (see "Frontend serving" below)
- `backend/migrations/` — Alembic migrations, hand-written Postgres DDL (see "Database" below)
- `backend/tests/` — pytest suite
- `backend/scripts/` — `e2e.py` (API checklist against a running server; also seeds its own demo
  org/Supabase Auth users on first run - see `ensure_demo_org()`), `seed_demo.py` (builds on
  `ensure_demo_org()` to seed richer CRM-module demo data - departments, worker-role employees,
  shifts/attendance, leave, a full recruitment pipeline, and varied worker reports including a
  confirmed cluster - so the staff dashboards have something to show instead of empty states;
  idempotent, per-section guarded, safe to rerun), `run_test.ps1` (Windows one-command test
  runner), `sample_sop.py`, `hi_multistep.mp3` (sample Hindi audio for manual testing)
- `docs/` — historical planning docs (`auth-plan.md`, `feature-plan.md`, `feature.md`) from
  before the Supabase/CRM migration; these describe decisions as they were made at the time and
  are **not** kept in sync with later refactors - do not treat them as current

## Commands

### Backend (run from `backend/`)

Needs a Supabase project. For local dev, the Supabase CLI's own stack gives you real
Postgres + Auth + Storage with no cloud account (just Docker):

```bash
supabase init && supabase start      # prints local URLs/keys; `supabase status` reprints them later
```

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt  # adds pytest, ruff
cp .env.example .env                 # then set the Supabase values (see supabase status) and an LLM key
alembic upgrade head                 # required: schema is not created on app startup, see Database below
uvicorn app.main:app --reload --port 8001

pytest                                # needs `supabase start` running; truncates+reseeds a fixed demo org per test
pytest tests/test_routing.py::test_route_assigns_lines_manager_not_supervisor  # single test
ruff check app tests                  # lint

alembic revision -m "..."              # scaffold a new migration (hand-write the DDL - see Database below)
```

### Frontend (run from `backend/frontend/`)

```bash
cp .env.example .env   # set VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY (same values as the backend's, VITE_-prefixed)
npm install
npm run dev       # Vite dev server with HMR; proxies /api to the backend on :8001
npm run build     # tsc -b && vite build -> dist/ (uvicorn --reload does NOT rebuild this on change)
npm run lint      # oxlint
```

After any frontend change, the backend won't see it until `npm run build` runs again — `uvicorn
--reload` only watches `app/`, not `frontend/`.

### Docker

```bash
docker build -t voice-to-sop backend \
  --build-arg VITE_SUPABASE_URL=... --build-arg VITE_SUPABASE_ANON_KEY=...
docker run --env-file backend/.env -p 8000:8000 voice-to-sop
```

Or `backend/docker-compose.yml` for the same thing without retyping flags: `docker compose up -d
--build` from `backend/`. It reads both the build args and the runtime env from the same
`backend/.env` - which means `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY` need to be duplicated
into that file too (Compose's `build.args` can only pull from its own `.env`/shell environment,
not from `env_file:`, so the plain `V2S_SUPABASE_*` vars aren't visible to the build stage; see
`.env.example`). It also binds the container to `127.0.0.1:8000` only (not `0.0.0.0`) and caps it
at `mem_limit: 2g` - deliberate for sharing a host with other services: Whisper-medium on CPU can
run 2.5-3GB RSS on first real use (lazy-loaded, so this only hits on the first transcription, not
at boot), so the cap makes that an isolated container restart via `restart: unless-stopped`
rather than a host-wide OOM risk. **If this container ever starts in a `Restarting (1)` crash
loop**, check `V2S_DATABASE_URL` first - the direct-connection host
(`db.<ref>.supabase.co`) can be IPv6-only on a cloud project (confirmed on a real project: it had
an AAAA record and no A record at all), which hangs forever from a host with no IPv6 route. Point
it at the Supavisor **session-mode** pooler instead (`aws-0-<region>.pooler.supabase.com:5432`,
username `postgres.<project-ref>`) - not transaction-mode (port 6543), which breaks psycopg3's
prepared-statement cache. Also worth knowing: removing the image (`docker rmi`) does **not**
reclaim the build cache BuildKit kept around underneath it (seen in practice: an 11GB image left
over 12GB of cache behind after the image itself was gone) - `docker builder prune -af` reclaims
that separately.

Two-stage build: a `node` stage runs `npm ci && npm run build` for the frontend (needs the
`VITE_SUPABASE_*` build args — Vite inlines them into the bundle at build time, not runtime; the
anon key is public-by-design, not a secret-handling concern), then its `dist/` is copied into
the `python` stage, along with `migrations/`/`alembic.ini`. The Python stage also bakes the
Whisper model checkpoints in at build time (see Dockerfile) so cold starts don't hit Hugging
Face — this makes `app/` changes bust a large layer-cache, so CI only runs the Docker build
manually (`workflow_dispatch`), not on every push. The container's `CMD` runs `alembic upgrade
head` before starting uvicorn, since schema is never auto-created on boot (see Database below).

## Architecture

### Request pipeline (voice-to-SOP)

ASR (fine-tuned Whisper per language, lazy-loaded and cached on first use, run over
silence-split windows) → LLM structuring (any OpenAI-compatible chat endpoint — Groq in
deployment, Ollama locally by default) → TTS (edge-tts). `app/asr.py`, `app/structuring.py`,
`app/tts.py`, `app/llm.py`.

### Auth (`app/auth.py`)

No account system **for workers, in any module** — this is structural, not a gap. Staff
(supervisor/manager/plant_head/hr_admin/recruiter) sign in via **Supabase Auth**
(`supabase.auth.signInWithPassword` from the frontend; there is no `POST /api/login`).
`current_person()` verifies the resulting JWT locally on every request — against Supabase's
public JWKS (`{supabase_url}/auth/v1/.well-known/jwks.json`, fetched via `jwt.PyJWKClient` and
cached in-process; current Supabase projects sign with a per-project ES256 key, not a shared
secret, so there is no JWT-secret setting to configure) — then resolves the signed-in user to
their `employees` row via a thin `profiles(id UUID → auth.users, employee_id → employees)`
bridge table. Role is read live from `employees` on every request, so a role change applies
immediately with no re-login, same as before this migration. Worker-facing routes
(`/api/report`, `/api/ask`, `/api/receipt/{receipt}`, `/api/machines`, `/api/machine/{id}/sop`)
are deliberately unauthenticated — this is intentional, not an oversight, so reporting a problem
never requires identifying yourself.

**`employees.role` includes `'worker'`** (added for the Workforce module's shift
scheduling/clock-in). This is additive, not a reversal of worker anonymity: a `'worker'`-role
row is a directory/scheduling record only and must **never** get a `profiles` row — no Supabase
Auth account, ever. The `reports` table still has zero FK to any employee, worker or otherwise;
a worker filing a voice report is exactly as anonymous as before. What changed is that a worker
can now be *named* for Workforce-module scheduling, via a supervisor operating a kiosk on their
behalf — see Workforce below.

Authorization is scope-based, not role-based alone, and enforced **twice**: once in Python
(`auth.scope_sql()` / `auth.author_scope_sql()` build a `WHERE line_id IN (...)` clause limiting
a manager/supervisor to the lines they run and a plant_head to their whole plant; `auth.org_admin`
gates hr_admin/plant_head-only writes like the employee directory, departments, and shift
definitions; `auth.recruiter_access` gates hr_admin/recruiter/plant_head-only recruitment
writes) and again at the database layer via **Postgres Row Level Security** on every table —
RLS is a backstop, not a replacement for the app-level checks, which stay for explicit intent
and tighter query plans. Always filter new routes through the appropriate scope helper rather
than trusting role name alone, and add a matching RLS policy in the same migration — see any
`migrations/versions/000N_*.py` for the pattern.

**Worker-route database access bypasses RLS entirely**, via a separate `service_role` connection
(`db.connect_service()`, distinct from the RLS-enforced `db.connect(person)`). This is the one
place a plain psycopg connection (not going through Supabase's PostgREST, which would do this
automatically) has to hand-roll what `auth.uid()` needs: `db.connect(person)` runs `SET LOCAL
ROLE authenticated` plus `SELECT set_config('request.jwt.claims', '<json>', true)` as the first
statements of every transaction (note: `SET LOCAL x = :param` does **not** accept bind
parameters in Postgres — that's a protocol limitation, not a SQLAlchemy one — so the claims JSON
must go through `set_config()`'s third argument instead). `db.connect_service()` just does `SET
LOCAL ROLE service_role`, which has `BYPASSRLS`.

**RLS + views footgun worth knowing before it costs you an hour**: `report_view` and
`step_edit_view` (and any future view over an RLS-protected table) **must** be created `WITH
(security_invoker = true)`. Without it, Postgres evaluates RLS on the underlying tables as the
*view's owner* (whoever ran the migration), not the querying role — silently leaking every row
to every caller regardless of the policies on the base tables. This was confirmed by actually
reproducing the leak, not just inferred from docs — see migration `0001_postgres_baseline.py`'s
comments for the full explanation.

**Self-referential RLS policies recurse.** A policy on `employees` that needs the caller's own
`plant_id` can't just subquery `employees` again inside its own `USING` clause — Postgres
re-evaluates the same policy for that inner query and recurses infinitely. Fixed with a
`SECURITY DEFINER` helper function (`public.current_employee_plant_id()`, in
`0001_postgres_baseline.py`) that bypasses RLS for just that one lookup; reuse it (don't
reinvent it) anywhere a new policy needs "the caller's own plant" without querying `employees`
directly from inside an `employees` policy.

### Database (`app/db.py` + `migrations/`)

**Supabase Postgres, via SQLAlchemy Core (`text()` + named binds) over `psycopg` v3 — no ORM,
no autogenerate.** `db.py` exposes two connection context managers: `connect(identity)` (RLS-
enforced, scoped to one signed-in staff member — `identity` is either a Supabase auth uid
string or an already-resolved person dict carrying one under `"_auth_uid"`) and
`connect_service()` (RLS-bypassing, for the worker-facing routes only — see Auth above).

**No `supabase-py` SDK dependency, on purpose.** It's never imported anywhere in
`app`/`scripts`/`tests` — every Supabase call already goes through raw `httpx` (Auth, Storage) or
`psycopg`/SQLAlchemy (Postgres) directly, per this section and Auth above. It used to be in
`requirements.txt` anyway, unused, and its own `httpx<0.28` pin silently conflicted with the
`httpx==0.28.1` pinned a few lines below — breaking `pip install -r requirements.txt` from
scratch (any fresh Docker build fails immediately; a long-lived local `.venv` can mask this since
it's never force-reinstalled against an updated pin, which is exactly how it went unnoticed).
Removed for both reasons. Don't re-add it.

**Nothing seeds or creates schema on app startup.** The old SQLite-era `db.init()` (idempotent
`CREATE TABLE IF NOT EXISTS` + demo-org seeding on every boot) is gone — a shared hosted
Postgres instance isn't a per-dev scratch file, so DDL only ever happens via `alembic upgrade
head`, run explicitly (locally, and as the first thing the Docker image's `CMD` does on every
deploy). For local dev/demo data, use `scripts/e2e.py`'s `ensure_demo_org()` instead (idempotent,
bails out rather than colliding if the target project already has unrelated data).

**`ensure_demo_org()`'s account creation only works against a cloud project because it uses the
Supabase admin API, not public signup** - confirmed by actually hitting this against a real cloud
project, not inferred from docs. Public `/auth/v1/signup` format-validates emails more strictly
on a hosted project than the local CLI stack and rejects fake-TLD demo addresses outright
(`email_address_invalid`); an address that does pass just trades that for the shared sender's
`over_email_send_rate_limit`, and either way an unconfirmed account can't sign in by password at
all. `_signup_or_signin()` instead calls `POST {supabase_url}/auth/v1/admin/users` with the
service-role key and `email_confirm: true` - no email sent, account usable immediately - falling
back to a password sign-in only on `422 email_exists` (already created, on a rerun). Don't revert
this to plain public signup on the assumption it only ever runs against the local stack.

**Every migration is hand-written Postgres DDL.** There is no schema-defining Python constant to
import the way `app.db.SCHEMA` once worked for SQLite — RLS policies, `SECURITY DEFINER`
functions, and `security_invoker` views are never things a tool can autogenerate, so the whole
schema (including plain tables) is written directly in each `migrations/versions/000N_*.py`.
When extending an existing table or view, match the pattern already in `0001_postgres_baseline.py`
rather than introducing a different migration style.

**SQLite → Postgres translations that bit us for real** (worth knowing before repeating them):
`INTEGER PRIMARY KEY` → `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` (inserting an explicit
id needs `OVERRIDING SYSTEM VALUE`, and doesn't advance the sequence — `setval()` it afterward if
you do this for seed data); `strftime()` defaults/date-math → `now()` / `created_at + interval
'N hours'`; SQLite's 2-arg scalar `MAX(a,b)` → `GREATEST(a,b)`; `INSERT OR IGNORE` →
`INSERT ... ON CONFLICT (...) DO NOTHING`; SQLite's null-safe `IS` between two columns → standard
SQL `IS NOT DISTINCT FROM`; a subquery in `FROM` needs an explicit alias (SQLite allows it bare,
Postgres doesn't); an untyped `NULL` bind parameter used only in `x IS NULL` gives psycopg's
extended protocol nothing to infer a type from — cast it (`CAST(:param AS text) IS NULL ...`,
not `:param IS NULL`); a bare `:param::text` short-cast right after a bind name isn't parsed
correctly by SQLAlchemy's `text()` — use `CAST(:param AS text)` instead.

The schema still has `report_view` / `step_edit_view` (the escalation-after-SLA and
worker-report clustering logic), now on Postgres syntax per the translations above, plus
`WITH (security_invoker = true)` — see Auth above for why that's load-bearing, not cosmetic.

### Worker report lifecycle (`app/routing.py`, `app/corrections.py`, `app/routes/report.py`)

A report is triaged into `kind` (machine/sop/understanding) + `severity`, then `routing.route()`
assigns it to the line's manager with an SLA deadline (24h if machine+high severity, else 72h),
and `routing.cluster()` links it to any other open report on the same machine/kind/step within a
30-day window. Once a cluster reaches 3 reports on kind `sop`, `corrections.draft()` proposes a
step-text edit; a manager approving it in the Inbox writes the next SOP version. Worker reports
never store audio — only the transcribed, triaged text. Both modules are plain functions taking
a `Connection` + ids/pre-fetched rows, with no FastAPI/HTTP concerns — `app/leave.py` (leave
balance deduction on approve) follows the exact same shape; match it, not a class-based service
layer, if you add similar "approve does a state transition plus one side effect" logic elsewhere.

### CRM modules (Employee / Workforce / HR)

Each follows the request pipeline's established conventions: a thin FastAPI router in
`app/routes/`, scope enforcement via the Auth-section helpers (`org_admin`/`recruiter_access`
for plant-wide or org-wide admin writes, `may_author_line`/`author_scope_sql` for line-scoped
operational data), and a matching RLS policy added in the same migration as the table.

- **Employee** (`app/routes/employees.py`, migration `0002_employee_module.py`): `employees`
  (now including `'worker'`-role rows, department/job-title/direct-manager/employment-status
  columns) + `departments`. Directory reads are plant-wide for any signed-in staff; writes are
  `org_admin` only.
- **Workforce** (`app/routes/workforce.py`, migration `0003_workforce_module.py`): `shifts`
  (plant-wide definitions, `org_admin`-gated) + `shift_assignments`/`attendance` (line-scoped,
  `may_author_line`-gated, `UNIQUE(employee_id, work_date)`). Clock-in/out is **kiosk-style**: a
  supervisor/manager operates it on behalf of a named worker at a shared device, behind normal
  staff auth — not a new anonymous worker-facing route, since a clock-in is inherently tied to
  one person's identity (unlike a problem report).
- **HR** (`app/routes/leave.py`, `app/routes/recruitment.py`, `app/leave.py`, migration
  `0004_hr_module.py`): leave is self-service for staff with an account (own-row-or-
  `org_admin`-in-same-plant RLS scope); recruitment (`job_postings`/`candidates`/`applications`)
  is `recruiter_access`-gated and scoped org-wide, not per-plant. Candidate resumes use real
  Supabase Storage: the backend issues a short-lived signed upload URL (service-role key, `POST
  {supabase_url}/storage/v1/object/upload/sign/{bucket}/{path}`) and the browser PUTs the file
  directly to Storage — the backend never sees the file bytes, only the resulting object path.
  Payroll is explicitly out of scope; the schema leaves room (`employees`, `attendance`,
  `leave_balances`) for it without rework if it's added later.

### Observability (`app/observability.py`, `app/metrics.py`, `app/logging_config.py`)

Structured JSON logs (one line per request: method/path/status/duration/request_id) and
Prometheus counters at `/metrics`, both wired as the *outermost* middleware layer so rate-limit
rejections and CORS failures are still logged/counted. Rate limits (`app/limiter.py`, slowapi)
are in-memory per-process — a multi-worker deployment would need a shared backend (Redis) for
them to hold across processes. Staff sign-in itself is rate-limited by Supabase, not this app.

### Frontend serving

The React app is a SPA using `HashRouter` (`#/machines`, `#/cards?machine=1`, etc.) specifically
so FastAPI can serve it as plain static files with no catch-all server route needed — every
client-side path lives after the `#` and never reaches the server. `main.py` mounts
`frontend/dist` at `/preview` only if that directory exists; if it's missing (frontend never
built), it logs a warning and skips the mount rather than failing — `StaticFiles` raises at
*import time* if its directory is absent, which would otherwise take every `/api/*` route down
with it. Keep this guard if touching that mount; pure-backend work (pytest, API-only dev)
shouldn't require Node/npm to be installed.

`lib/session.ts` wraps Supabase's client-side session (persisted in the browser's **local
storage**, not sessionStorage — it survives across tabs and browser restarts, unlike the old
HMAC-token system, which was explicitly per-tab). `hooks/useSession.ts`'s `useSession()` returns
a tri-state `Session | null | undefined`: `undefined` means Supabase's own async session
hydration hasn't resolved yet, distinct from `null` ("genuinely signed out") specifically so a
page refresh never bounces an already-signed-in user — `useRequireRole()`'s redirect effect
skips while `undefined`. Don't collapse this back to a two-state boolean; that was a real bug
caught by testing session persistence across a hard reload, not a hypothetical one.
`components/StaffNav.tsx` is the persistent tab bar across modules (SOP/Inbox/Employees/
Workforce/HR), role-filtered; it's absent for workers since they never have a session at all.

Framer Motion gotcha worth knowing before it costs you an hour again: a `motion.form` or
`motion.button` with an `exit` prop, rendered inside `AnimatePresence`, can silently swallow the
native click→submit default action after an interrupted animation — the synthetic `onClick`
fires but the browser's form submission doesn't. Keep the real `<form>`/`<button>` as plain
elements and use `motion.div` only as the animating wrapper around them.

### Testing conventions (`backend/tests/`)

`conftest.py`'s `client` fixture needs a real local Supabase stack (`supabase start`) running —
there's no SQLite file swap anymore. Per test, it truncates every table in the `public` schema
(auto-discovered via `pg_tables`, not a hand-maintained list — a hand-maintained list broke
twice already when new modules added tables, see the fixture's comments) via a single `TRUNCATE
... RESTART IDENTITY CASCADE`, then reseeds a fixed demo org (`OVERRIDING SYSTEM VALUE` to keep
the same ids old test assertions expect) and signs in 5 demo Supabase Auth users once per
session (`demo_auth` fixture — slow to create, so not redone per test; a local token's 3600s
expiry easily outlives a full run). `auth_headers(person_id)` is a fixture-returned closure, not
a plain function — tests take it as a parameter, not an import. The rate limiter's in-memory
store still needs the same per-test `limiter.reset()` it always did. No test hits a real LLM or
ASR model; `app.llm.call_json` and `app.asr`/ASR calls are monkeypatched where exercised.

Tampering with a real token for a "rejected" test (e.g. `test_tampered_token_rejected`) must
flip a character in the *middle* of the signature, not the last one — unpadded base64url's
final character can carry unused low bits for a signature whose byte length isn't a multiple of
3 (true of this project's ES256 signatures), so a last-character flip can decode to the exact
same bytes and the "tampered" token verifies as valid anyway. This was a real, intermittently
flaky test before the fix, not a hypothetical edge case.
