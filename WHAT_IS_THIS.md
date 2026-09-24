# What this project is

In plain language, with no code and no jargon.

---

## The problem

In an Indian factory, the person who really knows how a machine works is usually a
supervisor with fifteen or twenty years on the floor. He knows the order of the steps,
he knows which one will burn your hand, and he knows the small tricks that are not
written in any manual.

That knowledge is almost never written down.

Writing it down means sitting at a computer and typing a formal document, usually in
English. The supervisor may not type. He may not write English. And even if he can, it
takes an hour of his time to help somebody else. So it never happens.

Meanwhile the worker who has to follow the procedure may not read well in any language,
and may have come from a different state and speak a different language altogether.

So the knowledge stays trapped in one person's head. New workers learn by watching.
Mistakes get repeated. And when that supervisor retires, twenty years of knowing walks
out of the gate.

---

## What the product does

**The supervisor talks. The system turns it into cards.**

He picks up his phone and speaks for five minutes in Hindi or Marathi, the way he would
explain it to a new person standing next to him. He rambles. He goes out of order. He
repeats himself. That is fine — that is how people actually talk.

The system then does three things:

1. **Listens and writes it down** in the language he spoke.
2. **Sorts it out** — finds the real order of the steps even though he said them out of
   order, breaks it into one action per step, and marks the steps that involve danger:
   heat, current, sharp edges, chemicals, moving parts.
3. **Makes the cards** — one card per step.

Each card has:

- the step number
- a simple picture for the action
- one short line in the worker's language
- a **speaker button** — tap it and hear the step read out loud
- a red or yellow marking if that step is a safety step

Eight cards. Five minutes of talking. Nothing typed by anybody.

---

## Why cards

Because a worker standing at a machine is not going to read a two-page document.

He needs one thing at a time, big enough to see, with a picture, in his own language,
and a button he can press if he would rather hear it than read it. One card, one action.
Tap for the next one.

---

## The part that makes it different

Most systems stop there. The supervisor speaks, the cards get made, and that's the end
of it. The cards sit on the wall and slowly go out of date.

**This one has a second button on every card: a microphone.**

The speaker button lets information come *down* — from the supervisor to the worker.
The mic button lets it come back *up*.

So the operator at the machine, who cannot type and will never fill in a form, holds
the mic for eight seconds and says:

> *"The bolt is 17mm, not 15."*

That voice note attaches to that card. The next worker sees it. The supervisor sees it.

And when several people leave the same kind of note on the same card, the system writes
the correction and sends it to the supervisor for approval. He taps once. The card
updates for everyone.

**The cards get more correct the more they are used.**

In the first month, an SOP is one man's memory. After six months, it is the combined,
checked knowledge of everybody who has actually done the job.

---

## The other thing the cards quietly tell you

Because the cards are on phones, the system can see how they are being used — without
anyone filling in a report.

- A step replayed eleven times in a week means nobody understands it.
- A step skipped by two-thirds of the operators means it is probably impractical.
- A step everybody stalls on means something there is harder than it looks.

The supervisor opens his phone and sees *"step 4 was replayed 11 times."* He re-records
eleven seconds. Fixed.

No audit, no survey, no consultant.

---

## Languages

The supervisor speaks Hindi or Marathi. Real factory speech mixes in English words —
*"machine band karo"*, *"belt loose hai"* — and that is handled as normal, not as an
error.

The workers may not speak his language. Factories run on migrant labour: a Marathi
supervisor instructing people from Bihar, UP, Odisha. So the cards can be shown in each
worker's own language, with the audio in that language too. **He explains it once;
everyone gets it in the language they think in.**

---

## Why this can't just be done with ChatGPT

This is the question that will always get asked, and the answer is simple.

A general AI knows how a press brake works in general. It does not know how *your* press
brake works after twelve years of modifications, or that the guard on the number three
machine was bypassed, or that the lockout key sits in the supervisor's pocket so nobody
uses it.

That information is not on the internet. It is not in any manual. It is not in any
dataset anywhere in the world. It exists only as unwritten practice in the hands of
twenty people on one shop floor.

This product is the only thing that gets it out of their heads — and, through the mic
button, keeps getting it out, week after week, as reality changes.

A general model gives you a generic answer. In a safety situation, a confident generic
answer is worse than no answer, because it pushes aside the local knowledge that
actually keeps someone's hand attached.

---

## In one sentence

**A supervisor speaks for five minutes in his own language, and out come simple picture
cards that any worker can follow — and every worker who uses them can talk back, so the
cards keep getting more correct over time.**
