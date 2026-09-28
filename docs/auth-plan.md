# Plan — Sign-in for supervisors and managers

## Why

Right now anyone can do anything.

There is a login (`backend/app/routes/login.py:12`), but it asks for one password that
everybody shares: `V2S_AUTH_SECRET`. If you know it, you can sign in as any person —
including the plant head. There are no personal passwords.

Only six routes check the token at all. Everything else is open, so any stranger who can
reach the server can add a machine, or save a new SOP over a real one.

The `supervisor` role exists in the database but does nothing. Nobody signs in as a
supervisor, and no route asks whether you are one. On the screen, the role is just a word in
the web address: `machines.html?role=supervisor` (`static_preview/machines.html:43`). A
worker becomes a supervisor by editing the address bar.

This plan fixes those three things: personal PINs, a token that expires, and a role that the
server actually checks.

## Workers do not sign in

Workers get no account and no PIN.

The whole point of the reporting feature is that nobody knows who spoke. That is not a
promise in a document — it is built into the database. A report has no column for who sent
it, and the `people` table cannot even hold a worker (`role` only allows `supervisor`,
`manager`, `plant_head`). Reports are sorted by machine and line instead
(`app/routing.py:8-22`).

Giving workers logins would break that and buy nothing. So the worker's door stays one tap,
no sign-in.

## What we decided

- **Workers:** no login. Complaints stay sorted by machine and line.
- **Staff:** each person gets their own number PIN, stored scrambled (hashed) in the database.
  `V2S_AUTH_SECRET` is only used to sign tokens now, not to log in.
- **Staying signed in:** a token in `sessionStorage`, the same way `inbox.html:102-114`
  already does it.
- **The screen:** the "pick a role" page becomes a sign-in page. Your role comes from your
  token. The worker door stays on that page, with no sign-in.

## Steps

### 1. Store and check PINs — `app/auth.py`, `app/db.py`

Add a `pin_hash TEXT` column to `people` (`db.py:11-18`).

Databases that already exist need the column added. Do it in `db.init()` (`db.py:143`), just
after the schema runs:

```python
cols = {r["name"] for r in conn.execute("PRAGMA table_info(people)")}
if "pin_hash" not in cols:
    conn.execute("ALTER TABLE people ADD COLUMN pin_hash TEXT")
```

Two small helpers in `app/auth.py`. Both use Python's own library, so nothing new to install:

```python
def hash_pin(pin: str) -> str:
    """scrypt with a per-person salt, stored as salt_hex$hash_hex."""

def verify_pin(pin: str, stored: str | None) -> bool:
    """Constant-time compare via hmac.compare_digest. False when stored is NULL."""
```

Use `hashlib.scrypt(n=2**14, r=8, p=1)`. Someone with no PIN saved cannot sign in.

### 2. Demo PINs — `app/db.py`

`DEMO_ORG` (`db.py:115-127`) is plain SQL, and SQL cannot scramble a PIN. Leave it alone. In
`init()`, right after the demo data is added, set the five PINs in Python:

```python
DEMO_PINS = {1: "1111", 2: "2222", 3: "3333", 4: "4444", 5: "5555"}
```

Only on a brand-new database (`db.py:147-148`), so a real factory never gets PINs that are
written down in this file. List them in `TESTING.md`.

### 3. Sign in with a PIN — `app/routes/login.py`, `app/schemas.py`

`LoginRequest` becomes `{person_id, pin}`. Drop `secret`.

Look the person up, check the PIN, and answer `401 "wrong id or PIN"` for both a wrong PIN
and an id that does not exist. Today a missing person gets a `404` (`login.py:19`), which
quietly tells a stranger which ids are real.

### 4. Make tokens expire — `app/auth.py`

Today a token never dies (`auth.py:18-19`). One person has one valid token, forever. The only
way to cancel it is to change the shared secret, which cancels everyone's at once.

Now that a PIN is needed to get one, give it an end time:

- `issue_token` → `f"{person_id}.{exp}.{hmac(f'{person_id}.{exp}')}"`, where `exp` is a unix
  timestamp 12 hours out.
- `current_person` splits the three parts, checks the signature, then refuses an `exp` that
  has passed with `401`.

The role is still read fresh from the database on every request (`auth.py:28`), so changing
someone's role takes effect straight away.

### 5. Protect the authoring routes — `app/auth.py` and four route files

One new guard, next to `report_reader` (`auth.py:34`):

```python
def sop_author(person: Annotated[dict, Depends(current_person)]) -> dict:
    """Any signed-in staff member may author. The line check is per-route."""
```

And one helper, shaped like the `scope_sql` that already exists (`auth.py:41`):

```python
def may_author_line(person: dict, line_id: int, conn) -> bool:
    """plant_head: any line in their plant. Otherwise the line's own supervisor or manager."""
```

Where they go:

| Route | File | Change |
|---|---|---|
| `POST /api/machines` | `machine.py:33` | needs `sop_author`; `403` unless `may_author_line(req.line_id)` |
| `GET /api/lines` | `machine.py:45` | needs `sop_author`; show only the caller's own lines |
| `POST /api/sop` | `sop.py:14` | needs `sop_author`; find the machine's line, then the same check |
| `POST /api/structure` | `structure.py:10` | needs `sop_author` — costs LLM money, authoring only |
| `POST /api/transcribe` | `transcribe.py:17` | needs `sop_author` — costs ASR time, authoring only |
| `GET /api/sops` | `sop.py:47` | needs `sop_author`; limit to the caller's own lines |

**Leave these open.** They are the worker's path and must never ask for a token:
`GET /api/machines`, `GET /api/machine/{id}/sop`, `GET /api/sop/{id}`, `POST /api/report`,
`POST /api/ask`, `GET /api/receipt/{receipt}`, `POST /api/tts`, `GET /api/audio/{key}`,
`GET /api/health`, `POST /api/login`.

`POST /api/ask` runs ASR inside itself and still stays open — it is the worker's speak button.

### 6. One place for the session — `static_preview/app.js`

The shared `api()` helper sends no token. Add small helpers beside it, copied from the working
code in `inbox.html:102-127` so there is only one copy of it:

- `token()`, `saveSession({token, name, role})`, `session()`, `signOut()` — all on
  `sessionStorage`, each read and write wrapped in `try/catch`. A browser that blocks storage
  must not break the worker's pages.
- `authHeaders()`, and an `apiAuth()` that sends the caller back to `index.html` on a `401`.

### 7. Sign-in page — `static_preview/index.html`

Replace the three doors with:

- One big **worker** door, in Hindi, no sign-in → `machines.html`, with no `role` in the address.
- A **staff sign-in** form: person id and PIN → `POST /api/login` → `saveSession(...)` → send
  them where their role belongs: `supervisor` → `machines.html`, `manager` and `plant_head` →
  `inbox.html`.
- Already signed in? Go straight to that screen.

### 8. Read the role from the token, not the address — three pages

- `machines.html:43` stops reading `?role=`. It asks `session()` instead. A signed-in
  supervisor sees English wording, the "add machine" button, and links to `create.html`. No
  session means worker wording, Hindi, and links to `cards.html`. Remove `?role=` everywhere
  it is written or read.
- `create.html`: needs a supervisor session, or it sends you to `index.html`. Add
  `authHeaders()` to its transcribe, structure and save calls.
- `inbox.html`: delete its own private `TOKEN_KEY` block and use the shared helpers. Swap the
  `Server secret` box for a PIN box. Keep the 401/403 messages it already has
  (`inbox.html:226-234`) — the supervisor one still makes sense.
- Add a small sign-out link to the staff pages.

`cards.html` does not change. It is the worker's screen and only calls open routes.

### 9. Update the checker and the docs

- `scripts/e2e.py` signs in with `secret`; change it to `pin`. Add to `phase7_access`
  (`e2e.py:201-207`): wrong PIN → 401, faked or expired token → 401, a supervisor authoring on
  someone else's line → 403, and a plant head reading across both lines.
- `README.md`: the login line (`{person_id, secret}` → `{person_id, pin}`), the
  `V2S_AUTH_SECRET` row (it signs tokens now, it is not the login), and move the newly
  protected routes out of the "Open (no token)" table.
- `TESTING.md`: replace "person id 2 + `V2S_AUTH_SECRET`" with the demo PINs and the new
  landing page.
- `feature-plan.md`: note in Phase 7 that personal PINs replaced the shared secret, and that
  workers still have no account on purpose.

## Not in this plan

Changing or resetting a PIN, creating accounts from the screen, locking someone out after
repeated wrong PINs, and refresh tokens. And no worker identity, ever. Say these plainly in
the README's known limits instead of leaving them unsaid.

## How to check it works

1. Start the server from `backend/` with a **new** `V2S_DB_PATH`, so the demo PINs are created.
   Then start it again on the old database, to prove the added column works and that a person
   with no PIN gets `401`.
2. `POST /api/login {person_id: 2, pin: "2222"}` gives a token. Wrong PIN → `401`. Id that does
   not exist → the same `401`, word for word.
3. The worker's path, with no token anywhere: open `/preview/index.html`, tap the worker door,
   pick Press 1, play a card, hold the speak button, see the confirmation.
4. Supervisor: sign in as 1 / `1111`. The machine list is in English and has "add machine".
   Record and save an SOP on Press 1 (Line A). Try to add a machine to Line B → `403`. Check
   that `machines.html?role=supervisor` does nothing without a session.
5. Manager: 2 / `2222` opens the inbox. 1 (a supervisor) gets the 403 message. 5 still gets a
   `404` on a Line A report.
6. Change one character of a saved token → `401`. Build a token with a past `exp` → `401`.
7. `python scripts/e2e.py` against the running server. Every phase passes, including the
   longer `phase7_access`.
