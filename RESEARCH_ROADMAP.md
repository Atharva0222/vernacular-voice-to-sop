# Vernacular Voice-to-SOP — Research Roadmap to a Publishable Paper

A gap analysis of the current system against the 2025-26 literature, and a concrete list of
what to add so the work is defensible at a national or international venue.

---

## 1. Honest assessment of where the project stands today

The current build is a **working cascaded system**: Whisper fine-tune (Hindi/Marathi) →
OpenAI-compatible LLM (Groq) → edge-tts. That is an engineering artifact, not yet a paper.

What reviewers will say about it as-is:

| Objection | Why it lands today |
|---|---|
| "No novelty — this is three off-the-shelf models in a row." | True. ASR, LLM prompting, and TTS are all used zero-shot / off-the-shelf. |
| "No evaluation." | There are zero numbers in the repo. `jiwer` and `datasets` are in `requirements.txt` but no eval script exists. |
| "No baselines." | Nothing is compared against IndicConformer, Whisper large-v3, Seamless, or commercial APIs. |
| "No dataset." | No Hindi/Marathi *procedural, spontaneous, shop-floor* speech data is collected or released. |
| "No users." | The target population (low-literacy factory workers/supervisors) has never touched it. |
| "Task is undefined." | "Good SOP" is not operationalised — no schema spec, no gold annotations, no metric. |

**The good news:** three things already in the repo are genuinely paper-worthy if you measure
them instead of just shipping them.

1. **The silence-gap windowing in `backend/app/asr.py`.** You discovered empirically that the
   Hindi/Marathi fine-tunes garble audio over ~30s under both `chunk_length_s` stitching and
   native long-form generation, and you split on `librosa.effects.split` boundaries instead.
   This is exactly the long-form/hallucination failure mode that is an active 2025-26 research
   thread ([Whisper hallucination via hidden-representation steering](https://arxiv.org/pdf/2606.07473),
   [hallucination space projection](https://arxiv.org/html/2609.04561),
   [adaptive layer attention + KD](https://arxiv.org/pdf/2511.14219)). Nobody has
   characterised it specifically for *Indic community fine-tunes*. Measure it → that is a section.
2. **The stale `generation_config` incompatibility.** Community Indic Whisper checkpoints ship
   configs that crash modern `transformers`. This is a reproducibility finding about the Indic
   model ecosystem worth a paragraph and a table of which checkpoints are affected.
3. **The end-to-end task itself.** Spontaneous vernacular speech → executable safety-annotated
   SOP is not covered by existing SOP work, which is all English and all text-input
   ([SOPStruct](https://arxiv.org/abs/2504.00029),
   [Amazon's multi-agent SOP→code](https://aclanthology.org/2025.emnlp-industry.163.pdf),
   [SOP-Bench](https://arxiv.org/pdf/2506.08119)). The *speech-first, low-resource, low-literacy*
   framing is the white space.

---

## 2. The gap in the literature (your positioning statement)

Three research communities are adjacent but none covers this cell:

- **Indic ASR** — [Vistaar/IndicWhisper](https://www.isca-archive.org/interspeech_2023/bhogale23_interspeech.pdf)
  (59 benchmarks, best WER on 39, ~13.6 WER Hindi), [IndicVoices](https://huggingface.co/datasets/ai4bharat/IndicVoices)
  (23.7K hours, 22 languages, 76% extempore), [LAHAJA](https://arxiv.org/pdf/2408.11440)
  (multi-accent Hindi), [IndicConformer](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual).
  All stop at the transcript. None evaluate a **downstream task**.
- **SOP / procedural NLP** — SOPStruct (DAG/decision-tree representations), SOP-Bench, SOP-Maze,
  [SOPRAG](https://arxiv.org/pdf/2602.01858), [ordered-procedural-step reasoning](https://arxiv.org/pdf/2511.04688).
  All **English**, all **text-input**, all assume a clean written procedure exists.
- **HCI4D / ICTD** — [Medhi et al. on low-literate UI](https://courses.cs.washington.edu/courses/cse490c/18au/readings/medhi-thies-2015.pdf)
  (graphical + voice → 100% task completion), [Avaaj Otalo](https://dl.acm.org/doi/10.1145/1753326.1753434),
  [CGNet Swara](https://dl.acm.org/doi/10.1145/2160673.2160695). Rich on method, pre-LLM on technology.

> **Claim to stake:** *the first speech-native, low-resource pipeline and benchmark for converting
> spontaneous vernacular procedural narration into safety-annotated, executable SOPs, with an
> ASR-error-propagation analysis and a field evaluation with the intended low-literacy users.*

---

## 3. What to add — ranked by publication value per unit effort

### Tier 0 — non-negotiable (without these there is no paper)

#### 0.1 Build **VoiceSOP-Bench**, a small gold dataset
This is the single highest-value contribution. Everything else hangs off it.

- **Target:** 200-400 spontaneous Hindi + Marathi procedural narrations (3-6 min each) from real
  supervisors/operators; 8-15 SOPs per narration. Even 150 well-annotated items is publishable.
- **Recording protocol:** real shop-floor noise, phone mics, varied accents (follow LAHAJA's
  accent-stratified design). Record `wav` 16 kHz, log district/L1/age/gender.
- **Annotations per item:**
  - verbatim transcript (for WER/CER)
  - gold step list with canonical ordering
  - a **DAG of dependencies** (borrow SOPStruct's representation — sequential vs. parallel vs.
    conditional steps), not just a flat numbered list
  - `is_safety_warning` labels with a hazard taxonomy (heat / sharp / electrical / chemical /
    moving parts / PPE), double-annotated
  - icon keyword from a **closed vocabulary** (see 1.3)
- **Code-switching tags.** Shop-floor Hindi/Marathi is heavily English-mixed ("machine band karo",
  "gloves pehno", "temperature check karo"). Tag CS spans — this alone supports a whole analysis
  section and connects to [MUCS](https://arxiv.org/abs/2104.00235) and
  [Hindi-English code-mix Whisper adaptation](https://www.isca-archive.org/interspeech_2025/biswas25_interspeech.pdf).
- **Splits:** dev/test only is fine; you are evaluating, not training (unless you do 2.1).
- **Release** under CC-BY-4.0 with a datasheet.

**Inter-annotator agreement is mandatory.** Report Cohen's κ for safety labels, Kendall's τ for
step ordering between annotators. Reviewers will ask.

#### 0.2 Define the task formally and write an evaluation harness
Create `backend/eval/` with reproducible scripts. Metrics to report:

| Stage | Metric | Notes |
|---|---|---|
| ASR | WER, CER | Use `whisper_normalizer`'s **Indic** normalizer, **not** `BasicTextNormalizer` — it strips matras and silently inflates scores ([What is lost in Normalization?](https://arxiv.org/pdf/2409.02449)). |
| ASR | SN-WER | [Script-Normalized WER](https://arxiv.org/pdf/2606.02548) as a companion score, transliterate to canonical script first. |
| ASR | Entity/keyword WER | WER restricted to safety-critical terms and machine names. A missed "गर्म" matters more than a missed particle. |
| Structuring | Step-level precision/recall/F1 | Align predicted↔gold steps by embedding similarity (LaBSE / IndicSBERT), then score. |
| Structuring | **Kendall's τ** on ordering | τ = (C−D)/(½n(n−1)) over step pairs — the standard for procedural ordering. |
| Structuring | Safety-flag P/R/F1 | Report **recall separately and prominently** — a missed hazard is the costly error. |
| Structuring | Schema validity rate | % of LLM outputs parsing into your Pydantic schema on the first attempt (you already have a retry — measure how often it fires). |
| End-to-end | **AER (Answer Error Rate)** | Semantic divergence of the final SOP caused by ASR errors. 2025 work shows AER exceeds raw WER by 10-30 points in cascaded systems — quantifying this for Indic is a real contribution. |
| TTS | MOS / CMOS + intelligibility | Small native-speaker panel; plus round-trip WER (TTS output → ASR → compare). |
| System | Latency p50/p95, cost/hour, peak RAM | Deployability is part of the argument. |

#### 0.3 Run real baselines
Currently you compare against nothing. Minimum baseline grid:

- **ASR:** your `vasista22/whisper-hindi-medium` + `steja/whisper-small-marathi` vs.
  `openai/whisper-large-v3`, `ai4bharat/indic-conformer-600m-multilingual`,
  `ai4bharat/indic-seamless`, Bhashini/ULCA ASR API, and one commercial API (Google/Azure).
- **Structuring:** your Groq `gpt-oss-120b` prompt vs. a small local model (Llama-3.x-8B,
  Gemma-3, Qwen3), vs. a frontier model, vs. a *non-LLM* baseline (rule-based sentence splitting
  + keyword hazard lexicon). The rule baseline is important — reviewers want to know the LLM earns
  its cost.
- **Architecture:** cascaded (yours) vs. an **end-to-end speech LLM** (Qwen-Audio, SeamlessM4T +
  LLM, or an audio-input frontier model) fed the raw audio. This directly tests the
  cascaded-vs-E2E error-propagation question that ICASSP/Interspeech reviewers care about.

#### 0.4 The ablation your own code already begs for
You wrote a bespoke windowing strategy. Prove it:

| Long-form strategy | WER | Deletion rate | Hallucination rate | Latency |
|---|---|---|---|---|
| Whisper native long-form | | | | |
| `pipeline(chunk_length_s=30)` sliding window | | | | |
| Fixed 25s windows (no silence awareness) | | | | |
| **Silence-gap windows (yours)** | | | | |
| + VAD (Silero) pre-segmentation | | | | |

Measure hallucination explicitly (repeated n-gram loops, output on silence-only segments) —
that is the metric the 2026 hallucination papers use. Sweep `_SILENCE_TOP_DB` and
`_WINDOW_SECONDS`; a sensitivity curve is a cheap, high-credibility figure.

---

### Tier 1 — technical contributions that lift it from "system paper" to "research paper"

#### 1.1 Domain-adapted ASR via LoRA/PEFT
Fine-tune Whisper (or IndicConformer) on your shop-floor data with LoRA — the dominant
low-resource adaptation method in 2025-26. Expect large gains on machine names, units, and
code-switched imperatives. Report parameter count and training cost; PEFT on a single GPU is a
selling point for the "deployable in an Indian factory" narrative.
Pair with **synthetic entity-dense audio** from IndicF5/Indic Parler-TTS to cover rare machine
vocabulary — the [TTS-STT flywheel](https://arxiv.org/pdf/2605.03073) result says this closes
Indic ASR gaps where commercial systems fail.

#### 1.2 ASR-error-aware structuring
Right now `structuring.py` receives a plain string and trusts it. Two cheap, novel-ish upgrades:

- **Confidence-conditioned prompting.** Pass Whisper token log-probs; mark low-confidence spans
  as `[?word]` in the LLM input and instruct the model to treat them as uncertain. Ablate.
- **Noise-robustness study.** Inject synthetic ASR errors at controlled WER levels (5/10/20/30%)
  into gold transcripts and plot downstream SOP-F1 vs. WER. This produces the paper's money
  figure: *how much ASR quality does a usable SOP actually need?* — actionable for anyone
  deploying in a low-resource language.

#### 1.3 Icon grounding instead of free-text icon strings
`icon` is currently an unconstrained LLM string, which is unevaluable and unrenderable. Fix:

- Define a **closed pictogram vocabulary** (~60 concepts) mapped to a real icon set (Lucide is
  already loaded in your preview; ARASAAC is the standard open pictogram library for
  low-literacy/AAC use).
- Constrain the LLM to that vocabulary (enumerate in the schema / use structured outputs).
- Evaluate **icon selection accuracy** against gold, and — more interesting — run a
  **comprehension study**: can workers identify the intended action from the icon alone? This is
  the Medhi-style contribution and is what makes an HCI venue take it.

#### 1.4 Constrained decoding + self-verification
Replace "parse JSON, retry once" with (a) JSON-schema-constrained decoding (Outlines / vLLM
guided decoding / provider structured-output mode) and (b) a **verifier pass** that checks:
every gold-mentioned entity appears in some step; no step invented without support in the
transcript; ordering is a valid DAG. Report **step hallucination rate** — an LLM inventing a
safety step that the manager never said is the scariest failure mode in this application, and
naming and measuring it is a contribution.

#### 1.5 Interactive repair loop
A single-shot pipeline will always be brittle. Add a clarification turn: when the model's
confidence in ordering or a hazard flag is low, the system *asks back in the user's language*
("क्या मशीन बंद करने से पहले gloves पहनने हैं?") and the answer is folded in. Measure SOP-F1 with
0 / 1 / 2 clarification turns. This maps onto the agentic-dialogue hazard-identification thread
([HazDial](https://arxiv.org/html/2606.03812)) and is a strong CHI/COMPASS angle.

---

### Tier 2 — the human study (this is what makes it *publishable*, not just correct)

Automatic metrics alone will get "no evidence this helps anyone." Run a field evaluation.

- **Participants:** 20-30 shop-floor workers + 5-10 supervisors, at 2+ real sites.
- **Design:** within-subjects. Each participant performs tasks using (a) the existing paper/verbal
  SOP, (b) the generated text SOP, (c) the generated SOP with icons + TTS audio.
- **Measures:** task completion rate, time-on-task, **safety-step adherence rate** (the headline
  number), errors, recall after 24h, NASA-TLX for cognitive load, SUS, trust.
- **Supervisor side:** time to author an SOP by hand vs. by voice (expect a 5-20× reduction —
  that is your abstract's opening number), plus edit-distance between generated and
  supervisor-approved final SOP as a proxy for "how much correction was needed."
- **Qualitative:** semi-structured interviews, thematic analysis. Mixed-methods is the norm at
  ICTD/COMPASS/CHI.
- **Ethics:** IRB/institutional approval, informed consent in the local language (read aloud, not
  signed forms — literacy), fair compensation at/above local rates, no employer access to
  individual performance data (workers are in a power-asymmetric relationship with the site —
  reviewers *will* raise this). Publish an [augmented datasheet](https://dl.acm.org/doi/abs/10.1145/3593013.3594049)
  for the speech corpus.

---

### Tier 3 — deployment & systems contributions (cheap, and reviewers like them)

- **Offline/edge variant.** Factories have poor connectivity and data-governance concerns.
  Ship a fully-local config: `faster-whisper` (CTranslate2, ~4× faster, int8 quantisation) +
  a 3-8B local LLM via Ollama/llama.cpp + IndicF5 TTS. Report WER/F1/latency/RAM on a
  ₹40k mini-PC or a Jetson. A local-vs-cloud quality/latency/cost table is a strong figure and
  directly serves the "data never leaves the plant" argument.
- **Bhashini/ULCA integration.** For an Indian national venue this matters a lot: showing the
  pipeline runs on the government's national language stack makes the work policy-relevant and
  is an easy extra baseline column.
- **Swap edge-tts for an open, citable TTS.** `edge-tts` is an undocumented Microsoft endpoint —
  it is not reproducible, has no license for this use, and reviewers will flag it. Move to
  **IndicF5** (1417h, 11 languages, AI4Bharat) or **Indic Parler-TTS**, and keep edge-tts only as
  a fallback.
- **Load/cost characterisation.** Cold-start time (your Dockerfile bakes weights — quantify the
  win), throughput, cost per SOP in ₹ at Groq vs. local.

---

## 4. Concrete engineering backlog mapped to the repo

| # | Change | File(s) | Serves |
|---|---|---|---|
| 1 | `eval/` package: WER/CER/SN-WER, step-F1, Kendall τ, safety-F1, AER | new `backend/eval/` | 0.2 |
| 2 | Indic normalizer in eval (not `BasicTextNormalizer`) | `backend/eval/normalize.py` | 0.2 |
| 3 | Pluggable ASR backends behind one interface (HF pipeline / faster-whisper / NeMo IndicConformer / Bhashini) | refactor `app/asr.py` | 0.3, T3 |
| 4 | Long-form strategy as a config flag so the ablation is one loop | `app/asr.py`, `app/config.py` | 0.4 |
| 5 | Return token-level confidence from ASR | `app/asr.py` | 1.2 |
| 6 | Closed icon vocabulary + schema `Literal[...]` enum | `app/schemas.py` | 1.3 |
| 7 | Schema-constrained decoding, drop the string-parse retry | `app/structuring.py` | 1.4 |
| 8 | DAG output (`depends_on: list[int]`) instead of flat numbering | `app/schemas.py`, prompt | 0.1, 1.4 |
| 9 | Verifier pass + step-hallucination metric | new `app/verify.py` | 1.4 |
| 10 | Clarification-turn endpoint | new `routes/clarify.py` | 1.5 |
| 11 | IndicF5 TTS backend behind the existing `tts.py` interface | `app/tts.py` | T3 |
| 12 | Session logging (audio hash, timings, model versions, edits) for the field study | new `app/telemetry.py` | Tier 2 |
| 13 | Pin every model revision + seed; `results/` committed | repo-wide | reproducibility |
| 14 | **Rotate and remove the Groq key**, `.env.example` only | `backend/.env` | hygiene |

Do them in that order. Items 1-4 alone convert the repo into something you can write numbers about.

---

## 5. Suggested paper structure

1. **Introduction** — 300M+ Indian workers, SOP compliance gap, literacy barrier, why text-first
   SOP tooling fails, why speech-first is the right interface.
2. **Related work** — Indic ASR (Vistaar, IndicVoices, IndicConformer, LAHAJA); procedural/SOP
   generation (SOPStruct, SOP-Bench, SOP-Maze, Amazon SYNTACT); HCI4D low-literacy interfaces
   (Medhi, Avaaj Otalo, CGNet Swara). End with the empty cell.
3. **Task formulation** — spontaneous narration → safety-annotated SOP DAG; formal definition,
   schema, hazard taxonomy, icon vocabulary.
4. **VoiceSOP-Bench** — collection, demographics, annotation protocol, IAA, datasheet.
5. **System** — cascaded architecture; silence-gap long-form handling; confidence-conditioned,
   schema-constrained structuring; verifier; vernacular TTS + pictograms.
6. **Experiments** — ASR baselines; structuring baselines; cascaded vs. E2E; ablations
   (windowing, confidence conditioning, verifier, clarification turns); **SOP-F1 vs. WER curve**;
   latency/cost/offline table.
7. **Field study** — mixed-methods, safety-adherence as headline, authoring-time reduction.
8. **Error analysis** — code-switching failures, hallucinated steps, missed hazards by category,
   dialect/accent effects.
9. **Limitations & ethics** — two languages only, site count, over-trust in generated safety
   content, power asymmetry, liability of an automated SOP.
10. **Conclusion & release** — dataset, code, model weights.

**Headline numbers to aim for in the abstract:** (a) SOP authoring time reduced N×;
(b) safety-step recall X%; (c) safety-adherence improvement Y points over paper SOPs;
(d) usable SOPs still produced at Z% WER.

---

## 6. Venue strategy

### International

| Venue | Deadline (approx.) | Fit |
|---|---|---|
| **Interspeech 2026** (Sydney, Sep 27-Oct 1) | ~Feb-Mar 2026, 4 pages | Best fit for the ASR + long-form + code-switching + Indic story. Also has **Show & Tell** for the demo. |
| **ICASSP 2027** (after Barcelona 2026) | ~Sep 2026 | Signal-processing framing; strong for the windowing/hallucination ablation. |
| **ACL / EMNLP / NAACL — Industry or System Demo track** | rolling | Best fit for the LLM-structuring + constrained-decoding + benchmark contribution. EMNLP Industry accepted the closely-related Amazon SOP paper in 2025. |
| **LREC-COLING** | ~Oct | Ideal if the **dataset** is the primary contribution. |
| **ACM COMPASS / ICTD / CHI / CSCW** | varies | The field study belongs here. CHI if the interaction design and comprehension study are strong. |
| **Workshops:** WiNLP, AfricaNLP-style IndicNLP/SIGUL, Interspeech low-resource special sessions | | Low-risk first venue to establish the dataset. |

### National (India)

- **ICON** (International Conference on NLP, NLP Association of India) — the natural Indian venue.
- **NCVPRIPG / CODS-COMAD / IndiaHCI** — CODS-COMAD has a strong applied-ML track;
  IndiaHCI for the field study.
- **Bhashini / IndiaAI ecosystem workshops** — high policy visibility; integrating the ULCA API
  makes you directly relevant.

**Recommended sequence:** ICON or an Indic-NLP workshop first (establishes the dataset and gets
reviewer feedback cheaply) → Interspeech 2026 main paper + Show & Tell → COMPASS/CHI for the
field study as a separate, deeper HCI paper. One system, three papers, no salami-slicing
concerns if the contributions are genuinely distinct.

---

## 7. Minimum viable paper (if time is short)

If you can only do one thing: **Tier 0 in full** — 150-item dataset, eval harness, 4 ASR
baselines, 3 LLM baselines, the windowing ablation, and the SOP-F1-vs-WER curve. That is a
credible 4-page Interspeech or 8-page ICON paper without any field study, and everything in
Tiers 1-3 becomes the follow-up.

**What you must not submit:** the current repo plus a qualitative description. It will be desk-rejected.

---

## 8. Sources

- [Vistaar: Diverse Benchmarks and Training Sets for Indian Language ASR (Interspeech 2023)](https://www.isca-archive.org/interspeech_2023/bhogale23_interspeech.pdf)
- [IndicVoices dataset](https://huggingface.co/datasets/ai4bharat/IndicVoices) · [IndicVoices-R](https://github.com/AI4Bharat/IndicVoices-R)
- [LAHAJA: Multi-accent Hindi ASR benchmark](https://arxiv.org/pdf/2408.11440)
- [IndicConformer 600M multilingual](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual) · [IndicConformerASR](https://github.com/AI4Bharat/IndicConformerASR)
- [IndicF5 TTS](https://huggingface.co/ai4bharat/IndicF5) · [Indic Parler-TTS](https://github.com/AI4Bharat/Indic-TTS)
- [Generating Structured Plan Representation of Procedures with LLMs (SOPStruct)](https://arxiv.org/abs/2504.00029)
- [Structuring the Unstructured: Multi-Agent LLM Framework (EMNLP 2025 Industry)](https://aclanthology.org/2025.emnlp-industry.163.pdf)
- [SOP-Bench: Complex Industrial SOPs for Evaluating LLM Agents](https://arxiv.org/pdf/2506.08119)
- [Evaluating LLMs' Reasoning Over Ordered Procedural Steps](https://arxiv.org/pdf/2511.04688)
- [Adapting Whisper for low-resource Hindi-English Code-Mix speech (Interspeech 2025)](https://www.isca-archive.org/interspeech_2025/biswas25_interspeech.pdf)
- [Multilingual and code-switching ASR challenges for low resource Indian languages (MUCS)](https://arxiv.org/abs/2104.00235)
- [Whisper Hallucination Detection and Mitigation via Hidden Representation Steering](https://arxiv.org/pdf/2606.07473)
- [Reducing Hallucinated Transcripts via Hallucination Space Projection](https://arxiv.org/html/2609.04561)
- [Listen Like a Teacher: Mitigating Whisper Hallucinations](https://arxiv.org/pdf/2511.14219)
- [What is Lost in Normalization? Pitfalls in Multilingual ASR Evaluation](https://arxiv.org/pdf/2409.02449) · [whisper_normalizer](https://github.com/kurianbenoy/whisper_normalizer)
- [SN-WER: Script-Normalized WER for Multi-Script Indic ASR](https://arxiv.org/pdf/2606.02548)
- [The TTS-STT Flywheel: Synthetic Entity-Dense Audio Closes the Indic ASR Gap](https://arxiv.org/pdf/2605.03073)
- [Evaluating Speech-to-Text × LLM × Text-to-Speech Combinations](https://arxiv.org/pdf/2507.16835)
- [Enhancing Operational Safety via Agentic Dialogue Hazard Identification (HazDial)](https://arxiv.org/html/2606.03812)
- [User Interface Design for Low-literate and Novice Users (Medhi Thies)](https://courses.cs.washington.edu/courses/cse490c/18au/readings/medhi-thies-2015.pdf)
- [Avaaj Otalo: interactive voice forum field study (CHI 2010)](https://dl.acm.org/doi/10.1145/1753326.1753434)
- [CGNet Swara (ICTD)](https://dl.acm.org/doi/10.1145/2160673.2160695)
- [Augmented Datasheets for Speech Datasets (FAccT 2023)](https://dl.acm.org/doi/abs/10.1145/3593013.3594049)
- [Considerations for Ethical Speech Recognition Datasets (WSDM 2023)](https://dl.acm.org/doi/10.1145/3539597.3575793)
- [Bhashini APIs](https://bhashini.gitbook.io/bhashini-apis) · [ULCA](https://github.com/bhashini-dibd/ulca)
- [Interspeech 2026 Special Sessions & Challenges](https://assta.org/News/34282/Interspeech_2026_Special_Sessions_AND_Challenges) · [ICASSP 2026](https://2026.ieeeicassp.org/)
- [faster-whisper (CTranslate2)](https://github.com/SYSTRAN/faster-whisper) — via Context7, ~4× faster inference with int8 quantisation
