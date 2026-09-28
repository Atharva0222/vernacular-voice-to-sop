# Vernacular Voice-to-SOP

A supervisor narrates a procedure in Hindi or Marathi; the system turns it into simple
picture-and-voice SOP cards for the workers on that machine. Workers can hold a mic button
on any card to report a problem in their own language. The report is triaged against the SOP
into **machine**, **sop** or **understanding**, routed to the line's manager (never the
supervisor), and answered back as voice on the card.

`TESTING.md` walks through the whole loop by hand. `docs/` holds the worker feedback
specification and the plan it was built from.

## Pipeline

1. **ASR** — fine-tuned Whisper per language (`vasista22/whisper-hindi-medium`,
   `steja/whisper-small-marathi`), run over silence-split windows.
2. **Structuring** — an OpenAI-compatible LLM turns the transcript into numbered steps with
   a safety flag and an icon.
3. **TTS** — edge-tts reads each card back in the worker's language.

## Run locally

```bash
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
cp .env.example .env        # then set V2S_AUTH_SECRET and your LLM key
.venv/Scripts/uvicorn app.main:app --reload --port 8001
```

Open `http://localhost:8001/preview/index.html`. **Workers do not sign in**: the worker door
leads straight to the machine list, that machine's cards, and one speak button that the SOP
answers when it can. **Supervisors and managers sign in with a person id and PIN**, and the
role in the token decides the screen: supervisors add machines and record procedures for their
own lines, managers get the report inbox. A fresh database seeds demo staff with the PINs in
`TESTING.md`. Models download on first transcription.

Docker: `docker build -t voice-to-sop backend && docker run --env-file backend/.env -p 8000:8000 voice-to-sop`.

## Settings

All read from the environment or `backend/.env`, prefix `V2S_`.

| Variable | Default | What it does |
|---|---|---|
| `V2S_AUTH_SECRET` | *required* | Signs session tokens. Not a login credential: staff sign in with their own PIN. The app will not start without it. |
| `V2S_DB_PATH` | `<tmp_dir>/voice-to-sop.db` | SQLite file. An empty file is seeded with a demo plant, two lines and two machines. |
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
| `POST /api/login`, `GET /api/health` | sign in; health check |

**Sign in** with `POST /api/login {person_id, pin}` -> `Authorization: Bearer <token>`. PINs are
per person, hashed with scrypt; a person with no PIN cannot sign in. Tokens expire after 12
hours. A wrong PIN and an unknown id return the same `401`.

**Authoring token** (any signed-in staff member, held to the lines they run: a supervisor or
manager to their own, a plant head to their whole plant). Off-line writes get `403`.

| Route | Purpose |
|---|---|
| `POST /api/transcribe` | audio -> transcript |
| `POST /api/structure` | transcript -> steps (pure, stores nothing) |
| `POST /api/sop` | persist an SOP as the next version for its machine |
| `GET /api/sops` | every SOP on the caller's own lines |
| `POST /api/machines`, `GET /api/lines` | add a machine; the lines the caller may use |

**Manager token.** Supervisors get `403`; a manager sees only their own lines, a plant head
their whole plant.

| Route | Purpose |
|---|---|
| `GET /api/reports?status=&kind=` | inbox, confirmed clusters first |
| `GET /api/report/{id}`, `PATCH /api/report/{id}` | read one; set status or reply (voiced by TTS) |
| `GET /api/step-edits?status=` | card changes drafted from confirmed reports |
| `POST /api/step-edit/{id}/approve`, `.../reject` | approve writes the next SOP version |

## Privacy

No worker identity is captured anywhere. Report audio is deleted as soon as it is
transcribed and is never fetchable, so a voice cannot be recognised; only cleaned text is
kept. Reports are routed to the line's manager and are invisible to supervisors. On a small
line a manager may still guess who spoke from the content — the design reduces that risk, it
does not remove it.

## Verification

`python scripts/e2e.py` runs the plan's checklist against a running server: transcription
completeness, persistence, the three-way triage, the voiced reply, escalation, clustering,
access control and SOP self-correction.

## Known limits

- SQLite on an ephemeral disk: data is lost on redeploy. A volume or Postgres is needed
  before any pilot.
- Escalation is computed on read, so nothing escalates until a manager opens the inbox.
- Triage accuracy is unmeasured, and Marathi ASR is weaker than Hindi.
- Staff sign-in is deliberately minimal: there is no way to change or reset a PIN, no account
  creation screen, no lockout after repeated wrong PINs, and no refresh tokens. PINs are set
  in the database. Rotating `V2S_AUTH_SECRET` signs everyone out at once.
