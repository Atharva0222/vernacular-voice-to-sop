# Feature: Worker Voice Feedback ("Bolo")

In plain language. How a worker who cannot read or write can tell the people in charge
that something is wrong with the machine or with the SOP card.

---

## The problem

The worker is the one standing at the machine all day. He is the first person to notice
when something is off:

- the pedal feels loose
- the safety sensor has been removed
- the card says one thing, but the machine needs something else
- a step on the card does not work in real life

But today, that knowledge goes nowhere.

- **He cannot write it down.** Many workers cannot read or write, and a paper form or an
  app full of text is useless to them.
- **He is afraid to tell the supervisor.** The supervisor is judged on how few accidents
  and problems his line has. Reporting a problem can make the supervisor look bad, so
  workers stay quiet, or they speak and get ignored.
- **Nothing happens when he does speak.** When workers see that complaints lead to no
  change, they stop complaining.

This is not a guess. It is documented:

- Safe in India's CRUSHED reports on the Indian auto sector found that most injured
  workers lost fingers on power presses with problems a worker can see: a worn pedal, a
  damaged bolt, a missing sensor.
- Most of those injured workers were migrants with limited education or training.
- The same reports describe workers who told their supervisor about a faulty machine and
  were injured on it anyway.
- Safety research worldwide lists fear of the supervisor, difficult reporting forms, and
  lack of follow-up as the main reasons workers do not report problems.

(Sources are listed at the end.)

---

## What the feature does

**The worker speaks. The right person hears it. The worker is told it was heard.**

### 1. The worker speaks

The worker gives feedback in the easiest possible way, in Hindi or Marathi (more
languages later). There are two options:

- **One big mic button** on the SOP card he is using. He holds it and talks.
- **A phone number** he can call from any phone, even a basic one without internet. He
  calls, speaks, and hangs up.

He can say anything, in his own words:

> *"Pedal dheela hai, do din se aisa hi hai."*
> (The pedal is loose. It has been like this for two days.)

> *"Card bolta hai 15mm, par bolt 17mm ka hai."*
> (The card says 15mm, but the bolt is 17mm.)

### 2. The system understands it

The system:

1. **Writes down** what he said, in his language.
2. **Turns it into a clear paragraph** in plain language, removing repetition and filler.
3. **Compares it with the SOP** for that machine, step by step.

### 3. The system sorts the problem into one of three types

This is the important part. Because the system knows what the SOP says, it can tell what
*kind* of problem the worker is describing.

| Type | What it means | Example | Goes to |
|------|---------------|---------|---------|
| **Machine problem** | The SOP is fine, but the machine is not safe or not working properly | "The pedal is loose" | Manager + maintenance, marked urgent |
| **SOP problem** | The card itself is wrong or missing something | "The card says 15mm, the bolt is 17mm" | Manager, with a suggested change to the card |
| **Understanding problem** | The worker is doing the step differently from the card | He describes the steps in a different order | Manager, flagged as a training need |

A normal voice-reporting app cannot do this, because it does not know what the SOP says.

### 4. The report goes up, not sideways

The report goes to a **manager above the supervisor**, not to the supervisor of that line
and not to the person who looks after that machine.

This protects the worker from being ignored or blamed by the person closest to the
problem.

### 5. The worker hears back

When the manager acts, the worker gets a short **audio message in his own language**:

> *"Aapki baat suni gayi. Pedal kal theek hoga."*
> (You were heard. The pedal will be fixed tomorrow.)

This is what keeps workers speaking up. If they never hear back, they stop.

---

## Safety rules built into the feature

### The worker's voice stays private

A supervisor can recognise a worker's voice. So:

- The **audio recording is never sent** to the manager. Only the cleaned-up text goes up.
- The worker's **name is hidden by default**. The manager sees which machine and which
  step, not who said it.

### Nothing can be quietly ignored

If a **machine safety problem** is not acted on within a set time (for example, 24 hours),
it automatically goes **one level higher**. Even the manager cannot sit on it.

### Repeated reports count more

If several workers report the same thing about the same machine or step, the report is
marked as **confirmed** and moves up in priority.

---

## The full flow

```
Worker speaks (mic button or phone call, Hindi / Marathi)
        │
        ▼
Speech is written down in his language
        │
        ▼
Turned into a clear paragraph
        │
        ▼
Compared with the SOP for that machine and step
        │
        ▼
Sorted: Machine problem / SOP problem / Understanding problem
        │
        ▼
Sent to a manager above the supervisor (text only, name hidden)
        │
        ├── Not acted on in time? → Escalated one level higher
        │
        ▼
Manager acts
        │
        ▼
Worker hears back in his own language
```

---

## What already exists, and what is new

Voice-based safety reporting in Hindi and Marathi already exists, but it is built for
**safety inspectors and officers**, people who can already read, write, and fill in forms.

What is new here:

- It is built for **workers who cannot read or write**.
- It works through a **phone call**, not only an app.
- Every report is **compared with the SOP**, so the system knows whether the machine, the
  card, or the training is the problem.
- It **skips the supervisor** and **escalates automatically** if ignored.
- The worker is **told what happened** in his own language.

---

## Limits to be honest about

- **Technology cannot fix a bad culture on its own.** If management does not act on
  reports, workers will stop using this, just like any other system.
- **Speech recognition is weaker for Marathi** and for mixed Hindi-English factory speech
  than for plain Hindi. This needs testing with real factory recordings before relying on
  it.
- **Hiding the name is not perfect privacy.** In a small line with three workers, a
  manager may guess who spoke. The feature reduces the risk; it does not remove it.

---

## In one sentence

**A worker who cannot write calls a number or presses one button, says what is wrong in
his own language, and the system figures out whether the machine, the card, or the
training is the problem, sends it past the supervisor to someone who can fix it, and tells
the worker it was heard.**

---

## Sources

- Safe in India Foundation, CRUSHED reports on auto-sector worker injuries:
  https://www.safeinindia.org/post/crushed-2024-india-s-only-annual-report-on-workplace-injuries-and-workers-safety-in-the-automobile-1
- IndiaSpend, "Safety Rules Routinely Flouted In India's Factories" (June 2026):
  https://www.indiaspend.com/industry/safety-rules-routinely-flouted-in-indias-factories-986863
- Moneylife, same report, including workers' alarms being ignored:
  https://moneylife.in/article/safety-rules-routinely-flouted-in-indias-factories/80760.html
- Frontline (via PressReader), CRUSHED 2021 case of a worker who warned his supervisor:
  https://www.pressreader.com/india/frontline/20220225/281818582251239
- For Construction Pros, on fear of supervisor retaliation in near-miss reporting:
  https://www.forconstructionpros.com/business/construction-safety/article/10962393/how-to-improve-jobsite-safety-by-getting-workers-to-report-near-misses
- Quantum Compliance, on why workers stay silent:
  https://www.usequantum.com/near-miss-reporting-why-your-workers-stay-silent-and-how-to-change-that/
- Inviol, on near-miss underreporting research:
  https://www.inviol.com/post/near-miss-reporting-why-your-current-system-probably-underreports-by-90
- Inspectly360, existing Hindi/Marathi voice reporting for inspectors:
  https://www.inspectly360.com/apps/health-safety/incident-report-mobile-app
