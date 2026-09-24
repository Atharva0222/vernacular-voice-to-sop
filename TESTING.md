# Test the whole thing yourself

A walk through the full loop, in order: a supervisor's spoken procedure becomes cards, a
worker speaks a complaint into a card, a manager sees it and replies, and the card fixes
itself. About 30 minutes, most of it waiting for the speech models.

Everything below is one terminal in `backend/` plus a browser.

---

## 0. Before you start

You need:

- The Python environment in `backend/.venv` (already set up on this machine).
- An LLM endpoint in `backend/.env` (`V2S_LLM_BASE_URL`, `V2S_LLM_MODEL`, `V2S_LLM_API_KEY`)
  and a `V2S_AUTH_SECRET`. The app refuses to start without the secret.
- A microphone, for the part where you actually speak into a card.
- Patience: transcription runs on the CPU. A 10 second complaint takes a minute or two to
  come back. That is normal and the worker never waits for it.

Two things about this machine specifically:

- Downloads from Hugging Face need the certificate file, so put this in front of commands
  that may download a model:
  `$env:REQUESTS_CA_BUNDLE=".venv\windows-roots.pem"; $env:SSL_CERT_FILE=".venv\windows-roots.pem"`
- Use a scratch database so you never mix test data into anything real.

## 1. Start the server

In PowerShell, from `backend/`:

```powershell
$env:REQUESTS_CA_BUNDLE=".venv\windows-roots.pem"
$env:SSL_CERT_FILE=".venv\windows-roots.pem"
$env:V2S_DB_PATH="$env:TEMP\v2s-test\test.db"
$env:V2S_TMP_DIR="$env:TEMP\v2s-test"
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

Wait for `Application startup complete`, then open <http://localhost:8001/api/health> in the
browser. You should see `{"status":"ok"}`.

The first run creates the database and fills it with a demo factory:

| Who / what | id | Notes |
|---|---|---|
| Demo Supervisor (Line A) | 1 | Must never be able to read reports |
| Demo Manager (Line A) | 2 | This is you, for most of the test |
| Demo Plant Head | 3 | Reports land here when a manager is too slow |
| Demo Manager B (Line B) | 5 | Should not see Line A's reports |
| Press 1 (machine on Line A) | 1 | |
| Lathe 1 (machine on Line B) | 2 | |

Leave this terminal running. Everything else happens elsewhere.

## 2. Make the SOP cards (the supervisor's part)

Open <http://localhost:8001/preview/index.html>.

1. Pick **Hindi** in the language box.
2. Press **Record** and read this out loud, pausing a little between sentences:

   > मशीन चालू करने से पहले बिजली का स्विच बंद कर दें।
   > पैडल को पैर से धीरे धीरे दबाएं।
   > सत्रह नंबर का बोल्ट लगाकर प्लेट को कस दें।
   > काम खत्म होने के बाद मशीन को साफ करके रिपोर्ट लिखें।

3. Press Record again to stop, then press **Generate SOP**.

**What should happen:** after a minute or two you get one numbered card per sentence, each with
an icon, a speaker button, and a red mic button. The safety sentence should be marked
*Safety warning*.

**The thing to actually check:** every sentence you spoke turned into a card. If only the first
one shows up, the old transcription bug is back.

Press a speaker button — the card should read itself back to you in Hindi.

The page also saved this SOP against machine 1. From now on open it as:

<http://localhost:8001/preview/index.html?machine=1>

## 3. Speak a complaint into a card (the worker's part)

On that same page, **press and hold** the red mic on the *पैडल* card, say this, and let go:

> भैया यह पैडल बहुत ढीला हो गया है। दबाने पर वापस ऊपर नहीं आता। इससे चोट लग सकती है।

**What should happen:** the moment you let go, the card says **सुन लिया गया ✓**. That is the
whole point — the worker is told they were heard immediately, and is never left waiting while
the machine thinks.

Try a second complaint, on the *बोल्ट* card, about the card being wrong:

> कार्ड पर सत्रह नंबर का बोल्ट लिखा है। लेकिन यहां उन्नीस नंबर का बोल्ट लगता है।

And a third, on any card, about being confused:

> मुझे समझ नहीं आया कि प्लेट पहले कसनी है या मशीन पहले चालू करनी है।

Now leave this tab open and give it two or three minutes.

**Check nothing was kept:** look in `%TEMP%\v2s-test`. There should be no `report-*` files.
The recording is deleted as soon as it is transcribed, so nobody can ever play back a worker's
voice and recognise who it was. Only the cleaned text survives.

## 4. Read them as the manager

Open <http://localhost:8001/preview/inbox.html> in a new tab.

Sign in with **person id `2`** and the secret from `backend/.env` (`V2S_AUTH_SECRET`).

**What should happen:** your three complaints are there, each already sorted into one of three
kinds. This is the part a generic voice app cannot do, because it needs the SOP as context:

| Your complaint | Should be tagged |
|---|---|
| Loose pedal | **Machine** — the equipment needs repair |
| Wrong bolt number | **SOP card** — the card is wrong and needs changing |
| Confused about order | **Training** — the card is fine, the person needs teaching |

The wrong-bolt one should also show a **Suggested card text** line with the corrected step.

If a report still says *Processing*, transcription is not finished. Wait and reload.

## 5. Reply, and hear it back on the card

In the inbox, type a reply under the loose-pedal report:

> आपकी शिकायत मिल गई है। कल सुबह मैकेनिक पैडल ठीक करेगा।

Set the status to **acknowledged** and press **Send**.

Now go back to the worker tab (the cards). Within a few seconds a small **reply button**
appears on that card. Press it.

**What should happen:** you hear the manager's reply spoken aloud in Hindi. The worker never
had to read anything, and the loop is closed.

## 6. Check the supervisor really is shut out

This is the promise the whole feature rests on, so test it directly.

Close the inbox tab and open <http://localhost:8001/preview/inbox.html> in a fresh one — the
sign-in only lasts as long as the tab. Sign in as **person id `1`**, Demo Supervisor.

**What should happen:** refused. The supervisor cannot see a single report, not even their own
line's. Then try **person id `5`** (Demo Manager B, the other line): they sign in fine but see
none of your Line A reports.

## 7. The card fixes itself

Say the same wrong-bolt complaint two more times on the *बोल्ट* card (step 3), so there are
three altogether. Wait for them to process.

**What should happen:** in the inbox those three collapse into one entry marked
**Confirmed ×3**, and a **card change** appears at the top of the inbox showing the old text
and the proposed new text, with **Approve** and **Reject**.

Press **Approve**, then reload the worker page
(<http://localhost:8001/preview/index.html?machine=1>).

**What should happen:** the बोल्ट card now says *उन्नीस*, not *सत्रह*. Three workers said the
card was wrong, and the card changed. The old version is still in the database for audit.

## 8. The one that needs a nudge: escalation

A high-severity machine report that a manager ignores for 24 hours is supposed to go to the
plant head. You cannot wait a day, so move its deadline into the past. Leave the server
running and, in a second PowerShell window in `backend/`, run:

```powershell
.venv\Scripts\python.exe -c "import sqlite3, os; p = os.path.join(os.environ['TEMP'], 'v2s-test', 'test.db'); c = sqlite3.connect(p); n = c.execute('UPDATE reports SET escalate_after = ? WHERE kind = ?', ('2000-01-01T00:00:00Z', 'machine')).rowcount; c.commit(); print('backdated', n)"
```

Reload the inbox. (The report must still be **open** — if you set it to acknowledged in step 5,
set it back to open first.)

**What should happen:** that report now carries an **Escalated to plant head** badge. Note the
honest limit: nothing escalates until somebody opens the inbox. It is worked out when the page
is read, not pushed to anyone.

---

## If you would rather have it all checked for you

One command runs every step above except the browser parts, using recorded clips instead of
your voice, and prints PASS or FAIL for each. With the server running on port 8001:

```powershell
.venv\Scripts\python.exe scripts\e2e.py
```

It ends with `16 passed, 0 failed`. It takes about ten minutes, nearly all of it transcription.

## When something looks wrong

| What you see | What it usually is |
|---|---|
| Server won't start, complains about `auth_secret` | `V2S_AUTH_SECRET` missing from `backend/.env` |
| Only the first sentence became a card | The transcription window is wrong — it should be 4 s in `app/asr.py` |
| A report is stuck on *Processing* | Still transcribing. A minute or two per report on CPU |
| A report says *failed* | Look at the server terminal. Usually the LLM endpoint or an empty recording |
| Mic button does nothing | The browser blocked the microphone. Allow it for `localhost` |
| Inbox is empty after signing in | You signed in as the wrong person. Line A reports need person id 2 |
| Errors about certificates | Set `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` as in step 0 |

## Start over

Stop the server and delete `%TEMP%\v2s-test`. The next start builds a fresh database with the
demo factory in it. Do this after any change to the database structure, because existing
tables are never altered in place.
