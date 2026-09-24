# Bolo → Karo: Frontend Concept & Multilingual Plan

Design direction for the two interfaces, and the plan to make the whole product
vernacular-first rather than English-first.

---

## 0. Correcting the starting premise

> "Currently the manager will give the SOP in the English language."

Not quite — the backend is the opposite. `app/schemas.py` defines
`Language = Literal["hi", "mr"]`, `app/asr.py` loads Hindi and Marathi Whisper
fine-tunes only, and the structuring prompt in `app/structuring.py` ends with
*"Keep step text in the ORIGINAL language the manager used. Do not translate."*

**English is the one language the pipeline cannot currently accept.**

What is English is the *interface*: every button, label, and status string in
`static_preview/index.html` — "Record", "Generate SOP", "Stage 1/3 — Transcribing
audio…", "Safety warning". A Marathi foreman looks at an English control panel,
speaks Marathi into it, and gets Marathi back. The product is vernacular; the
chrome is not. That is the actual gap, and it is embarrassing in a demo.

The real language work is in §4. First, the design.

---

## 1. The structural idea: this is two products, not one page

The current preview is one scrolling page that does everything. That is why it
feels like "a form that makes cards." The insight that unlocks the whole design:

**Authoring and consuming are done by different people, in different places, under
different constraints, minutes or months apart.**

| | **Bolo** (बोलो — "speak") | **Karo** (करो — "do") |
|---|---|---|
| Who | Supervisor, foreman, line in-charge | Operator, helper, new joinee |
| Literacy | Reads fluently, often bilingual | May not read at all |
| Device | Own phone or tablet, in hand | Wall tablet, shared phone, or **paper** |
| Environment | Office or quiet corner of the floor | Noise, glare, gloves, grease |
| Session | 5 minutes, once | 30 seconds, every shift |
| Job | Get what's in my head out, correctly | Do the next thing, safely |

Two surfaces, one data model. Designing them as one page is what makes it generic.
Designing them as two is the contribution — and it is exactly the split the
HCI4D literature says matters.

Name the product after the promise: **Bolo → Karo.** Speak, then do.

---

## 2. Design plan

### 2.1 Colour — the Indian safety colour code, used for its real meaning

The palette is not decoration and not a brand mood. It is
**IS 9457 / BIS industrial safety signage**, which every one of these workers already
reads on the walls around them. Colour carries meaning, so it is never spent on anything else.

| Token | Hex | Meaning in the signage code | Where it appears |
|---|---|---|---|
| `--mandatory` | `#0057B8` | Blue — *you must do this* | Primary actions, normal steps, the record button |
| `--caution` | `#F5B100` | Yellow — *hazard, take care* | Safety-warning steps, low-confidence spans |
| `--prohibition` | `#E8442A` | Red — *stop, do not* | Lockout/stop steps, destructive actions, errors |
| `--safe` | `#007A3D` | Green — *safe condition, done* | Completed steps, confirmations |
| `--floor` | `#EEF1F0` | — | Page base: cool machine-paint grey-green, not cream |
| `--steel` | `#8A9490` | — | Rules, inactive, secondary text |
| `--petrol` | `#0F2A2E` | — | Text and dark surfaces: deep blue-green, not a tinted black |

Consequence worth stating out loud: **a card is never yellow for emphasis.** Yellow
means a hazard is present. If the colour lies, the worker stops trusting it, and the
safety-adherence number you want in the paper collapses.

### 2.2 Type — Devanagari as a first-class citizen, not a fallback

Most Indian-language interfaces set Devanagari in whatever the system serves up, at
Latin metrics, and it looks broken — matras clipped, wrong optical weight next to
English words in the same sentence. For a code-mixed product that is fatal.

- **Body / UI: [Mukta](https://github.com/EkType/Mukta)** (Ek Type, Mumbai — Girish
  Dalvi & Yashodeep Gholap). One family, seven weights, covering Devanagari,
  Gujarati, Gurmukhi, Tamil **and** Latin, drawn so no script dominates. Dainik Jagran
  and Lokmat set their online editions in it — *the audience already reads this
  typeface every morning.* It also future-proofs the Gujarati/Punjabi/Tamil expansion
  in §4 with zero type work.
- **Numerals & wordmark: [Sarpanch](https://fonts.google.com/specimen/Sarpanch)** —
  squared, industrial Devanagari + Latin. Step numbers are the one place the type gets
  to be loud, and a squared face reads as machine-shop rather than startup.

Setting rules:
- Devanagari gets **more leading than Latin** — matras live above and below the line.
  `line-height: 1.62` for Devanagari, `1.45` for Latin runs.
- Never below **16px** for Devanagari anywhere; **28px minimum** in Karo.
- In a code-mixed line ("machine बंद करो"), Latin and Devanagari must sit at matched
  optical weight. Mukta does this; a Latin-first stack with a Noto fallback does not.
- Line length under 60 characters — Devanagari runs wider per word than Latin.

### 2.3 Layout

**Bolo — the waveform is the spine.**

The recording is the source of truth, so it stays on screen permanently and everything
hangs off it. Not a progress bar that disappears: a persistent object you can point at.

```
┌──────────────────────────────────────────────────────┐
│  बोलो                          मराठी ▾   [ • रेकॉर्ड ] │
├──────────────────────────────────────────────────────┤
│  ▁▃▅█▇▅▃▁▂▅█▆▃▁▁▃▇█▅▂▁▄▆█▇▄▂▁▃▅▇▆▃▁▂▄▆▅▃▁          │  ← sticky
│  ╵    ╵      ╵  ╵        ╵      ╵     ╵   ╵          │  ← one tick per step
│  1    3      2  5        4      6     7   8          │  ← SPOKEN order
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌────┬───┬──────────────────────────────┬────┐      │
│  │ 1  │🧤 │ हातमोजे घाला                   │ ▶  │      │
│  └────┴───┴──────────────────────────────┴────┘      │
│                                                      │
│  ┏━━━━┳━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━┓      │
│  ┃ 2  ┃ ⚡ ┃ मशीन बंद करा — करंट आहे        ┃ ▶  ┃ ⚠   │  ← yellow
│  ┗━━━━┻━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━┛      │
│                                                      │
│  ┌────┬───┬──────────────────────────────┬────┐      │
│  │ 3  │🌡 │ ~~तापमान~~ चेक करा             │ ▶  │      │  ← uncertain word
│  └────┴───┴──────────────────────────────┴────┘      │
│                                                      │
│              [ मजुरांना पाठवा → ]                      │
└──────────────────────────────────────────────────────┘
```

Single column, left-aligned, 62ch max. Cards sit on the page; they do not each get a
drop shadow and a rounded border. Only the hazard card gets a heavy rule, because only
the hazard card has something to say.

**Karo — one step, nothing else.**

```
┌────────────────────────────────┐
│ ████████░░░░░░░░░░░   ३ / ८     │
├────────────────────────────────┤
│                                │
│                                │
│            ⚡                   │   ← pictogram, ~40% of screen
│                                │
│                                │
│     मशीन बंद करा                 │   ← 34px+
│     करंट आहे                     │
│                                │
│         ◀  ▶ ऐका  ▶             │   ← autoplays once on arrival
│                                │
├────────────────────────────────┤
│  ┃ धरून ठेवा — समजले ┃           │   ← hold 1.5s, hazard steps only
└────────────────────────────────┘
```

No scroll. No nav. Thumb-sized targets at the bottom edge where a gloved hand reaches.
On a hazard step the whole screen floods `--caution` and the advance button is replaced
by a **press-and-hold acknowledgement** — deliberate friction, and it emits the
safety-adherence event your field study needs.

### 2.4 Principles

1. **Every generated thing traces back to a moment in the audio.** Nothing appears
   without provenance.
2. **Colour is a safety code.** It is never spent on emphasis.
3. **Karo must work with zero reading.** If it needs a text label to be usable, it fails.
4. **One motion moment.** The untangle (§3.1). Everything else is instant.

### 2.5 Plan reviewed against the brief

Three things I changed after a first pass, because they were defaults rather than choices:

- **Dropped a dark shop-floor theme.** Near-black + one bright accent is the current
  house style of every AI-generated page, *and* it is wrong here: LCD screens in direct
  Indian daylight are more legible light-on-dark inverted. Karo is high-luminance.
- **Dropped the generic card kit.** The first sketch gave every step the same radius,
  border and soft shadow. Now weight is information: a normal step is a plain row, a
  hazard step is heavy-ruled. Sameness was hiding the one thing that matters.
- **Dropped `01 / 02 / 03` display numerals** as decoration — then put numbers back,
  large, because this content genuinely *is* a sequence and the number is the thing a
  worker calls out to a colleague ("teen number pe atka hoon").

---

## 3. The eight features that make it a demo people remember

Ranked by wow-per-effort. The first three are what you show on stage.

### 3.1 The Untangle — the hero moment

Managers narrate out of order. Your prompt already reorders them silently. **Show the
reorder.** On generation, the cards first appear in *spoken* order against the waveform,
then arcs sweep them into *logical* order and settle.

It lasts 1.2 seconds, happens once, and it is the only non-user-triggered motion in the
product. It is also the single clearest way to communicate what the system actually did
that a dictation app would not.

Research tie-in: this is Kendall's τ made visible. Put the figure in the paper.

### 3.2 Provenance scrubbing — tap a card, hear him say it

Every step carries the audio offsets it came from. Tap the step number and the waveform
scrubs there and plays **the manager's own voice**, not TTS.

This is the trust mechanism. A supervisor asked to sign off on a machine-written safety
procedure has exactly one question — *"did it make this up?"* — and this answers it in
one tap. It is also, not coincidentally, the UI for the step-hallucination metric
(roadmap §1.4): a step with no audio to point at is a fabricated step.

Backend: return word/segment timestamps from Whisper, carry them through structuring,
add `source_spans: list[tuple[float, float]]` to `Step`.

### 3.3 One narration → every worker's language

**This is the feature with the most real-world value in the entire product, and nobody
is building it.**

Indian factories run on migrant labour. A Marathi supervisor in Pune is instructing
workers from Bihar, UP, Odisha and West Bengal. He narrates once, in Marathi. Every
worker's phone shows the SOP in *their* language, with audio in *their* language.

- Translate with [IndicTrans2](https://github.com/ai4bharat/IndicTrans2) —
  `ai4bharat/indictrans2-indic-indic-dist-320M` is small enough to run alongside
  everything else, `indic-indic-1B` if quality demands it. 22 scheduled languages.
- Synthesise with [IndicF5](https://huggingface.co/ai4bharat/IndicF5) (11 languages,
  1417h) — which you should move to anyway, since `edge-tts` is an undocumented endpoint
  that will not survive review.
- Safety spans are translated with the hazard label pinned, never re-inferred, so a
  warning cannot be lost in translation.

Demo moment: three phones side by side — Marathi, Hindi, Odia — same voice, same
moment, three languages. That is the photograph that goes in the talk.

### 3.4 Confidence as ink, and repair-in-place

Whisper knows when it is guessing; the interface currently hides that. Render
low-confidence spans in `--caution` with a dotted underline. Tap one and the mic opens
for **that phrase only** — say the machine name again, it patches into the transcript,
and only the affected step re-runs.

A supervisor fixing three words is a 10-second interaction. Re-recording a 5-minute
narration because the model misheard "बुश" is why people abandon these tools.

Backend: token log-probs out of `asr.py`, plus a partial re-structure endpoint.

### 3.5 It asks you back

When ordering or a hazard flag is uncertain, the system asks — out loud, in the
manager's language — and listens:

> *"गॅस बंद करण्यापूर्वी हातमोजे घालायचे का?"*

Two taps, voice in, voice out, done. This turns a brittle one-shot pipeline into a
30-second conversation, and it is where the accuracy actually comes from. Ablate it at
0/1/2 turns for the paper (roadmap §1.5).

### 3.6 Print to floor — the QR-per-step sheet

The real artifact on an Indian shop floor is **a laminated A3 sheet zip-tied to the
machine.** Not an app. Design for that honestly instead of pretending everyone has a
phone in hand at the press.

Export an A3 poster: pictogram grid, step numbers in Sarpanch at 60pt, hazard steps in
yellow, and **a QR code per step** that plays that step's audio on any scanned phone.
Paper for the glance, phone for the detail. No app install, no login, no training.

Cheap to build, and it is the slide that convinces a plant manager.

### 3.7 Karo works offline, on a ₹6,000 Android

PWA, service-worker cached, audio pre-fetched on handoff. Connectivity inside a shed
with metal walls is bad and plants are rightly nervous about process audio leaving the
premises. Pair with the local-inference config (roadmap Tier 3: `faster-whisper` int8 +
local LLM + IndicF5) and the whole thing runs on a mini-PC in the supervisor's office.

"Your voice never leaves the plant" closes deals.

### 3.8 Live drafting while he talks

Steps materialise as he speaks rather than after he stops — partial hypotheses from a
streaming pass ([whisper_streaming](https://github.com/ufal/whisper_streaming) or
`faster-whisper` + VAD), reconciled by your existing silence-window batch pass on stop.

Genuinely magical to watch. Also the most likely to look broken if the partials churn,
so build it last and gate it behind a flag.

---

## 4. Making it actually multilingual

### 4.1 What's wrong now

| Problem | Where |
|---|---|
| Every UI string is English | `static_preview/index.html` throughout |
| Only `hi` / `mr` accepted | `schemas.py:5`, `asr.py:17-20`, `tts.py:7-10` |
| Code-mixed Hindi-English cannot be represented | same |
| Output language is forced to equal input language | `structuring.py` prompt |
| LID falls back to `hi` silently on anything unrecognised | `asr.py:124` |
| `edge-tts` covers only a handful of Indian voices | `tts.py` |

### 4.2 The model change: narration language ≠ SOP language

One line of schema is the whole unlock.

```python
# schemas.py
Language = Literal["hi", "mr", "en", "gu", "bn", "or", "ta", "te", "kn", "pa"]

class GenerateRequest(BaseModel):
    narration_language: Language | Literal["auto"] = "auto"
    output_languages: list[Language]           # fan out to the crew
    script: Literal["native", "latin"] = "native"
```

Everything in §3.3 follows from that.

### 4.3 Code-mixing is the normal case, not an edge case

Real shop-floor Marathi is *"machine चा belt loose आहे, पहिले power off करा."* Treat
Hindi-English and Marathi-English mixing as a first-class input mode, not noise:

- Add `hi-en` / `mr-en` as narration modes; don't force the LID to pick a side. The
  current `detect_language()` runs whisper-tiny over the whole clip and takes one token
  — on mixed audio it will flip depending on which 30 seconds it saw.
- Keep English technical terms **in Latin script** in the output. Transliterating
  "bearing" to "बेअरिंग" makes it *less* readable to the fitter who knows the part by its
  English name off the box.
- This connects straight to the MUCS and Interspeech-2025 code-mix literature — an
  evaluation slice worth its own table.

### 4.4 Script choice, separately from language choice

Plenty of younger workers read Hindi faster in Latin script than Devanagari
("Romanagari"). Offer a per-viewer toggle — same language, different script, via
`indic-transliteration`. Costs almost nothing and is a measurable comprehension result
for the field study.

### 4.5 Localising the chrome — and mostly avoiding the need

Bolo needs real localisation: `hi`, `mr`, `en` to start, strings in JSON, `lang` and
`dir` set properly, Mukta loaded for all three.

**Karo should barely need it.** If the worker view is doing its job, it is a pictogram,
a sentence in the worker's own language, and two buttons. Every chrome string you can
delete is a string you never have to translate into twenty-two languages — and a barrier
you remove for someone who cannot read any of them.

---

## 5. Backend work this implies

Ordered so each step ships something visible.

| # | Change | Files | Unlocks |
|---|---|---|---|
| 1 | Word/segment timestamps from Whisper; `source_spans` on `Step` | `asr.py`, `schemas.py`, `structuring.py` | 3.1, 3.2 |
| 2 | Token log-probs surfaced per span | `asr.py`, `schemas.py` | 3.4 |
| 3 | `narration_language` / `output_languages` / `script` split | `schemas.py`, all routes | 3.3, §4.2 |
| 4 | IndicTrans2 translation stage | new `app/translate.py` | 3.3 |
| 5 | IndicF5 TTS backend behind the existing interface | `tts.py` | 3.3, review-proofing |
| 6 | Closed pictogram vocabulary as a schema enum | `schemas.py`, prompt | 3.6, Karo, roadmap §1.3 |
| 7 | Partial re-structure endpoint (one step, not the whole SOP) | new `routes/repair.py` | 3.4 |
| 8 | Clarification turn endpoint | new `routes/clarify.py` | 3.5 |
| 9 | A3 + QR export | new `routes/export.py` | 3.6 |
| 10 | Code-mix LID policy; stop the silent `hi` fallback | `asr.py` | §4.3 |
| 11 | Acknowledgement / view telemetry from Karo | new `app/telemetry.py` | field study |
| 12 | Streaming partial transcripts (WebSocket) | new `routes/stream.py` | 3.8, last |

Items 1–3 are the foundation; 4–6 are the demo; the rest is depth.

---

## 6. Build order

**Sprint 1 — stop looking like a form.** Localise Bolo's chrome into Hindi/Marathi/English,
load Mukta and Sarpanch, apply the safety colour code, split the page into Bolo and Karo
routes. No backend changes. The product will already feel unrecognisable.

**Sprint 2 — provenance.** Backend items 1–2, then the waveform spine, tap-to-hear,
confidence ink.

**Sprint 3 — the untangle and the fan-out.** Items 3–5. This is the demo.

**Sprint 4 — the floor.** Karo properly: pictogram vocabulary, hold-to-acknowledge,
offline PWA, A3/QR export, telemetry.

**Sprint 5 — conversation and streaming.** Items 7, 8, 12.

---

## 7. Why this also helps the paper

Nothing above is decoration; each piece produces a number the roadmap already asked for.

| Frontend feature | Becomes |
|---|---|
| The untangle | Kendall's τ, visualised — the paper's figure 1 |
| Provenance scrubbing | Step-hallucination rate; the trust instrument |
| Confidence ink + repair | Confidence-conditioned prompting ablation |
| Clarification turns | 0/1/2-turn ablation curve |
| Hold-to-acknowledge | Safety-adherence rate — the field study's headline |
| Pictogram vocabulary | Icon comprehension study (the Medhi-style contribution) |
| Script toggle | Devanagari vs. Latin comprehension result |
| Multi-language fan-out | The deployment story, and the migrant-labour motivation |
| A3 + QR export | Why the intervention survives after the researchers leave |

A system paper with a field study and a demo track submission comes out of the same
build. Interspeech Show & Tell exists for exactly this.

---

## 8. References

- [Mukta (Ek Type)](https://github.com/EkType/Mukta) · [Mukta Devanagari](https://ektype.in/mukta-devanagari.html) · [Tiro Devanagari Hindi](https://fonts.google.com/specimen/Tiro%2BDevanagari%2BHindi) · [New wave of Indian type design](https://design.google/library/new-wave-indian-type-design)
- [IndicTrans2](https://github.com/ai4bharat/IndicTrans2) · [indictrans2-indic-indic-dist-320M](https://huggingface.co/ai4bharat/indictrans2-indic-indic-dist-320M) · [indictrans2-indic-indic-1B](https://huggingface.co/ai4bharat/indictrans2-indic-indic-1B)
- [IndicF5 TTS](https://huggingface.co/ai4bharat/IndicF5)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [whisper_streaming](https://github.com/ufal/whisper_streaming)
- [Adapting Whisper for Hindi-English code-mix (Interspeech 2025)](https://www.isca-archive.org/interspeech_2025/biswas25_interspeech.pdf) · [MUCS code-switching challenge](https://arxiv.org/abs/2104.00235)
- [User Interface Design for Low-literate and Novice Users (Medhi Thies)](https://courses.cs.washington.edu/courses/cse490c/18au/readings/medhi-thies-2015.pdf)
- See `RESEARCH_ROADMAP.md` for the full evaluation and venue plan.
