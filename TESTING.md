# Test the whole thing yourself

A walk through the full loop, in order: a supervisor's spoken procedure becomes cards, a
worker speaks a complaint into a card, a manager sees it and replies, and the card fixes
itself. About 30 minutes, most of it waiting for the speech models.

Everything below is one terminal in `backend/` plus a browser. One script,
`backend/scripts/run_test.ps1`, does all the setup for you.

## How to run it

Open PowerShell in `backend/` and pick one:

```powershell
.\scripts\run_test.ps1 -Manual     # server up, you test it in the browser (this walkthrough)
.\scripts\run_test.ps1             # no browser: runs every check for you, ~10 min
```

Then open <http://localhost:8001/preview/>. The worker walks straight in; staff sign
in with an id and PIN, and the role decides the screen. The pages are:

| Page | Who it is for | What it does |
|---|---|---|
| `/preview/` | everyone | The worker's door, and the staff sign-in |
| `/preview/#/machines` | worker | Pick a machine, then read its cards |
| `/preview/#/cards?machine=1` | worker | That machine's cards, plus one speak button to ask or report |
| `/preview/#/machines` | supervisor | Signed in, the same page lists only their lines and can add a machine |
| `/preview/#/create?machine=1` | supervisor | That machine's current cards, or record its first version |
| `/preview/#/inbox` | manager | Reports, replies, and card changes to approve |

Opening a staff page without signing in bounces you back to the sign-in.

Each machine keeps its own SOP, so cards are always read per machine. The worker's two pages
are entirely in Hindi; the supervisor's and manager's pages are in English.

---

## 0. Before you start

You need:

- The Python environment in `backend/.venv` (already set up on this machine).
- An LLM endpoint in `backend/.env` (`V2S_LLM_BASE_URL`, `V2S_LLM_MODEL`, `V2S_LLM_API_KEY`)
  and a `V2S_AUTH_SECRET`. The app refuses to start without the secret.
- A microphone, for the part where you actually speak into a card.
- Patience: transcription runs on the CPU. A 10 second complaint takes a minute or two to
  come back. That is normal and the worker never waits for it.

The script handles the two fiddly things about this machine itself: the certificate file
Hugging Face downloads need, and a scratch database in `%TEMP%\v2s-test` so test data never
mixes into anything real.

## 1. Start the server

In PowerShell, from `backend/`:

```powershell
.\scripts\run_test.ps1 -Manual
```

It prints `server healthy` and the two links. Leave this terminal running; Ctrl+C stops it.
Add `-Fresh` to start from an empty database, or `-Port 8002` to use another port.

Open <http://localhost:8001/api/health> in the browser. You should see `{"status":"ok"}`.

The first run creates the database and fills it with a demo factory:

| Who / what | id | PIN | Notes |
|---|---|---|---|
| Demo Supervisor (Line A) | 1 | `1111` | Must never be able to read reports |
| Demo Manager (Line A) | 2 | `2222` | This is you, for most of the test |
| Demo Plant Head | 3 | `3333` | Reports land here when a manager is too slow |
| Demo Supervisor B (Line B) | 4 | `4444` | |
| Demo Manager B (Line B) | 5 | `5555` | Should not see Line A's reports |
| Press 1 (machine on Line A) | 1 | | |
| Lathe 1 (machine on Line B) | 2 | | |

Those PINs are seeded only into a brand-new database, so a real deployment never gets them.
Workers have no id and no PIN anywhere in this table, which is the point.

Everything else happens in the browser.

## 2. Make the SOP cards (the supervisor's part)

Open <http://localhost:8001/preview/> — the home page. Sign in under
**Supervisor or manager** as **id `1`, PIN `1111`** (Demo Supervisor, Line A). You land on the
machine list, which shows only Line A: signing in as someone else would show a different list.

Pick **Press 1** from the machine list. Each machine has its own
SOP, so the procedure you record belongs to the machine you picked. A machine that is not on
the list yet is added there with **Add a machine** - name it, choose its line, and it opens
ready to record.

A machine that already has cards shows them instead of a recorder. Press 1 is empty on a fresh
database, so you get the recorder straight away; come back later and you will see its cards
with **Record a new version** underneath.

1. Pick **Hindi** in the language box.
2. Press **Record** and read this out loud, pausing a little between sentences:

   > मशीन चालू करने से पहले बिजली का स्विच बंद कर दें।
   > पैडल को पैर से धीरे धीरे दबाएं।
   > सत्रह नंबर का बोल्ट लगाकर प्लेट को कस दें।
   > काम खत्म होने के बाद मशीन को साफ करके रिपोर्ट लिखें।

3. Press Record again to stop, then press **Make the cards**.

**What should happen:** after a minute or two the page hands you over to Press 1's card page:
one numbered card per sentence, each with an icon, a speaker button, and a red mic button. The
safety sentence should be marked *Safety warning*. The raw transcript is not in your way - it
is folded away under *What was heard* on the recording page.

**The thing to actually check:** every sentence you spoke turned into a card. If only the first
one shows up, the old transcription bug is back.

Press a speaker button — the card should read itself back to you in Hindi.

This SOP is saved against machine 1. The worker reaches the same cards from the home page by
choosing **Worker** then **Press 1**, or directly at:

<http://localhost:8001/preview/#/cards?machine=1>

## 3. Speak to the machine (the worker's part)

The worker does not pick a card. At the bottom of the card page there is one red **speak**
button. **Press and hold** it, talk, and let go. What happens next depends on whether the cards
already answer you.

First say something the SOP does answer - you did the steps in the wrong order:

> मैंने पहले मशीन चालू कर दी, फिर प्लेट कसी। क्या यह ठीक है?

**What should happen:** after a minute or two the page speaks back to you in Hindi, telling you
what the card says to do. Nobody else is involved, and nothing about it is stored - a worker
asking a question is never something a manager can see.

Now say something the SOP does not answer, and let go:

> भैया यह पैडल बहुत ढीला हो गया है। दबाने पर वापस ऊपर नहीं आता। इससे चोट लग सकती है।

**What should happen:** the moment you let go it says **सुन लिया गया ✓**. That is the whole
point - the worker is told they were heard immediately, and is never left waiting while the
machine thinks. A loose pedal is not written on any card, so this one goes to the manager and
the page says so.

Try a second one, about a card being wrong:

> कार्ड पर सत्रह नंबर का बोल्ट लिखा है। लेकिन यहां उन्नीस नंबर का बोल्ट लगता है।

And a third, about being confused:

> मुझे समझ नहीं आया कि प्लेट पहले कसनी है या मशीन पहले चालू करनी है।

Now leave this tab open and give it two or three minutes.

**Check nothing was kept:** look in `%TEMP%\v2s-test`. There should be no `report-*` files.
The recording is deleted as soon as it is transcribed, so nobody can ever play back a worker's
voice and recognise who it was. Only the cleaned text survives.

## 4. Read them as the manager

Open <http://localhost:8001/preview/#/inbox> in a new tab.

It sends you to the sign-in if you are not already a manager there. Sign in as **id `2`,
PIN `2222`** (Demo Manager, Line A).

**What should happen:** only what the SOP could not answer is here, each already sorted by
kind. This is the part a generic voice app cannot do, because it needs the SOP as context:

| What you said | Where it went |
|---|---|
| Loose pedal | Inbox, tagged **Machine** — the equipment needs repair |
| Wrong bolt number | Inbox, tagged **SOP card** — the card is wrong and needs changing |
| Wrong order / confused | **Not here.** The SOP answered it out loud on the worker's page |

The wrong-bolt one should also show a **Suggested card text** line with the corrected step.

**The thing to actually check:** the question the SOP answered is nowhere in this inbox, under
any filter. A worker asking how to do their job is not a thing their manager gets to watch.

If a report still says *Processing*, transcription is not finished. Wait and reload.

## 5. Reply, and hear it back on the machine

In the inbox, type a reply under the loose-pedal report:

> आपकी शिकायत मिल गई है। कल सुबह मैकेनिक पैडल ठीक करेगा।

Set the status to **acknowledged** and press **Send**.

Now go back to the worker tab (the cards). Within a few seconds the speak bar at the bottom
says the manager has replied, and a green **play button** appears next to it. Press it.

**What should happen:** you hear the manager's reply spoken aloud in Hindi. The worker never
had to read anything, and the loop is closed.

## 6. Check the supervisor really is shut out

This is the promise the whole feature rests on, so test it directly.

Close the inbox tab and open <http://localhost:8001/preview/> in a fresh one — a
sign-in only lasts as long as the tab. Sign in as **id `1`, PIN `1111`**, Demo Supervisor.

**What should happen:** you land on the machine list, not the inbox, and going to
`/preview/#/inbox` by hand bounces you straight back out. The supervisor cannot see a single
report, not even their own line's.

Then sign in as **id `5`, PIN `5555`** (Demo Manager B, the other line): they reach the inbox
fine but see none of your Line A reports. While signed in as them, the machine list offers only
Line B, and trying to save a card for Press 1 is refused.

Two more worth a try: the wrong PIN for a real id, and a PIN for an id that does not exist.
Both say exactly **"Wrong id or PIN"**, so nobody can discover which ids are real.

## 7. The card fixes itself

Say the same wrong-bolt complaint two more times with the speak button (step 3), so there are
three altogether. Wait for them to process.

**What should happen:** in the inbox those three collapse into one entry marked
**Confirmed ×3**, and a **card change** appears at the top of the inbox showing the old text
and the proposed new text, with **Approve** and **Reject**.

Press **Approve**, then reload the worker page
(<http://localhost:8001/preview/#/cards?machine=1>).

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

One command does everything above except the browser parts: it starts the server on a scratch
database, waits for it, runs every check with recorded clips instead of your voice, prints PASS
or FAIL for each, and stops the server again. From `backend/`:

```powershell
.\scripts\run_test.ps1
```

It ends with `19 passed, 0 failed` and `ALL CHECKS PASSED`. It takes about ten minutes, nearly
all of it transcription. Useful switches:

| Switch | What it does |
|---|---|
| `-Fresh` | Delete the scratch database first, so the run starts from nothing |
| `-Manual` | Only start the server and leave it up, for the walkthrough above |
| `-Keep` | Leave the server running after the checks, to poke at the result |
| `-Port 8002` | Use a different port |

The server's own output goes to `%TEMP%\v2s-test\server.log` and `server.log.err`.

## When something looks wrong

| What you see | What it usually is |
|---|---|
| Server won't start, complains about `auth_secret` | `V2S_AUTH_SECRET` missing from `backend/.env` |
| Only the first sentence became a card | The transcription window is wrong — it should be 4 s in `app/asr.py` |
| A report is stuck on *Processing* | Still transcribing. A minute or two per report on CPU |
| A report says *failed* | Look at the server terminal. Usually the LLM endpoint or an empty recording |
| Mic button does nothing | The browser blocked the microphone. Allow it for `localhost` |
| An old page shows, with no role options | A browser cache from before the pages split. Restart the server, then reload with Ctrl+F5 |
| Inbox is empty after signing in | You signed in as the wrong person. Line A reports need person id 2 |
| Sign-in says "Wrong id or PIN" | Check the id and PIN against the demo table above. An old database has no PINs at all - delete it and restart |
| A staff page bounces to the home page | The session ended, or that role does not belong on that page. Sign in again |
| Saving a card is refused with 403 | That machine is not on one of your lines. Sign in as its line's supervisor |
| Errors about certificates | Start through `run_test.ps1`; it sets the certificate file for you |

## Start over

The database gained a column with the speak feature, so the first run after it needs a fresh
one. Stop the server and run `run_test.ps1 -Fresh`, or delete `%TEMP%\v2s-test`. The next start builds a fresh database with the
demo factory in it. Do this after any change to the database structure, because existing
tables are never altered in place.
