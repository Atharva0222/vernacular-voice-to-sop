# Setup on another PC (cloud Supabase project)

Assumes you're pointing at an existing cloud Supabase project (not the local
`supabase start` Docker stack). Needs Git, Python 3.x, and Node.js installed.

## 1. Clone

```bash
git clone <your-repo-url>
cd "<repo-folder>/backend"
```

## 2. Backend

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` and set, from your Supabase project dashboard:
- `V2S_SUPABASE_URL`
- `V2S_SUPABASE_ANON_KEY`
- `V2S_SUPABASE_SERVICE_ROLE_KEY`
- `V2S_DATABASE_URL` — use the **Supavisor session-mode pooler** host
  (`aws-0-<region>.pooler.supabase.com:5432`, user `postgres.<project-ref>`),
  **not** the direct `db.<ref>.supabase.co` host. The direct host can be
  IPv6-only on a cloud project and will just hang on a host with no IPv6 route.
- an LLM key (for the structuring step)

Then:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

## 3. Frontend (separate terminal)

```bash
cd backend/frontend
cp .env.example .env
```

Edit `.env` — same Supabase project, same values as the backend's, just
`VITE_`-prefixed:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Then:

```bash
npm install
npm run dev
```

Vite proxies `/api` to the backend on `:8001`. After any frontend change meant
to show up through the FastAPI-served `/preview` bundle, run `npm run build`
too — `uvicorn --reload` only watches `app/`, not `frontend/`.

## 4. (Optional) Seed demo data

```bash
cd backend
python scripts/e2e.py        # seeds base demo org + Supabase Auth users
python scripts/seed_demo.py  # richer CRM demo data; idempotent, safe to rerun
```

## Not covered here: `pytest`

The test suite truncates and reseeds the entire `public` schema on every run
and expects a local `supabase start` stack. Don't point it at this cloud
project unless it's a disposable one — it does not protect real data.
