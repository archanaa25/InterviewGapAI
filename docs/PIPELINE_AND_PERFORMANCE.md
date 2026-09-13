# Pipeline stages and the bottlenecks we removed

How the candidate journey is assembled, and the engineering decisions taken
along the way to make it fast enough and reliable enough to put in front of a
person.

Every number in this document comes from a recorded measurement in the
repository, not from recollection. The sources are named at each claim so a
reader can re-run them. Where a change did not produce the improvement we
expected, that is recorded too — several of the most useful findings were
negative.

---

## Part 1 — The stages

Seven stages run between a candidate uploading a resume and reading their
result. Four are model-backed, two are retrieval-backed, and the last is
deliberately neither.

| # | Stage | What it produces | How it runs |
|---|---|---|---|
| 1 | Resume extraction | Structured resume → `Resume` | One model call, small model |
| 2 | Resume evidence analysis | Evidence level per competency → `ResumeAnalysis` | Eight concurrent model calls: one per competency, plus a summary |
| 3 | Interview planning | Question allocation across competencies → `InterviewPlan` | One model call, bounded repair loop |
| 4 | Question selection | Ten frozen questions → `InterviewQuestionSet` | Question RAG over Pinecone, concurrent retrieval |
| 5 | Interview | The candidate's answers → `InterviewProgress` | No model. Pure UI state |
| 6 | Answer evaluation | Concept judgements → `InterviewEvaluation` | Evaluation RAG + bounded agent, parallel per question |
| 7 | Scoring and learning plan | `InterviewScorecard`, `LearningPlan` | No model. Deterministic Python |

### The boundaries that matter

**Stages 1–3 produce a plan; stage 4 is a separate call.** The gateway splits
there on purpose. The plan screen renders after stage 3, and question selection
runs when the candidate clicks Start — moving a multi-second wait behind
something worth reading rather than in front of it.

**Stage 5 is deliberately inert.** Answering a question triggers no model call
and no retrieval. It records the answer, writes the run to disk, and advances.
All assessment happens once, after the complete answer set exists, so nothing
the candidate does mid-interview can be shaped by partial grading.

**Stage 7 owns every number.** The evaluation agent returns concept judgements
and no scores. Scoring is deterministic Python, which means a score can be
recomputed, audited, and have its policy changed without re-running an
interview. It also means the model is never asked to do arithmetic it has no
reason to be good at.

---

## Part 2 — How the bottlenecks were found

The first version of the intake was slow in a way nobody could act on: a single
spinner, then roughly fifty seconds later, a plan. "It feels slow" is not a
defect report, so the first piece of work was measurement, not optimisation.

`scripts/evaluate_intake_latency.py` runs the pipeline in two arms — baseline
shape and optimised shape — across five fixture resumes with repeats, and
writes `data/eval/intake_latency_report.json`: per-stage wall time, call counts,
input/output/reasoning token counts, completion rate, and a written reason for
each change.

Two decisions in that harness did more for the quality of the conclusions than
any individual optimisation:

- **Medians across repeated runs, never a single sample.** The provider varies
  enough between calls that one timing is noise.
- **Completion rate reported alongside latency.** A stage that got faster but
  less reliable is a worse trade for the candidate, and a latency-only report
  would have hidden that. This caught a real case (see issue 4).

The measurement also produced the finding that reframed everything after it.

### The per-request floor

A trivial structured call — the smallest possible round trip — costs this much
before any real work happens:

| Model | Min | Median |
|---|---|---|
| gpt-5.6 | 5.04s | 7.34s |
| gpt-5.5 | 2.83s | 4.97s |
| gpt-5.4 | 1.37s | 2.57s |
| gpt-5.4-mini | 1.00s | 1.03s |
| gpt-5.4-nano | 1.43s | 1.69s |

**Latency is dominated by per-request overhead, not by generation.** That single
table redirected the work: the wins available were in *how many requests*, *how
they overlap*, and *which model each one needs* — not in trimming prompts.

---

## Part 3 — The issues, and what was done

### 1. Intake was a fifty-second blank wall

**Symptom.** All three intake sections stayed empty until every model call had
returned, then appeared at once.

**Diagnosis.** Not a latency problem — a *perceived* latency problem. The work
was already staged; the UI just wasn't showing it.

**Change.** The gateway gained an `on_result` callback so a caller can paint a
stage while the next is still in flight. All three sections render immediately
and fill as their stage lands.

**Result.** Profile at ~8s, evidence at ~29s, plan at ~46s, instead of nothing
until ~50s. Total time barely moved; the experience changed completely.
*(commit `6dade8a`)*

This is the cheapest category of win in the whole project, and it was available
before a single call was made faster.

### 2. Resume analysis was seven assessments in one serial call

**Symptom.** The slowest stage of the intake at 8.29s.

**Diagnosis.** The seven competency assessments are *independent readings of the
same resume*. Emitted from one call they were serial output tokens; there was no
dependency forcing them to be sequential.

**Change.** Fan out to one model call per competency plus one for the summary —
eight concurrent calls. The stage now costs the longest single assessment
rather than the sum of all of them.

**Result. 8.29s → 3.25s, a 60.9% reduction** — the largest single win in the
pipeline. Cost: 1 call → 8 calls, and input tokens rose from 1,790 to 12,436,
because the resume is re-sent per call. That trade was worth taking, and it is
worth stating plainly rather than hiding.

It also bought a new failure mode, which the code names directly: eight
concurrent requests are eight chances to meet a transient overload, and any one
failing fails the stage for the candidate. The fan-out spends reliability, and
the retry policy in issue 7 is what buys it back.
*(`intake_latency_report.json`, stage "resume analysis")*

### 3. Extraction was paying for reasoning it never used

**Symptom.** Extraction cost a full large-model round trip.

**Diagnosis.** The token counts showed it: **zero reasoning tokens** on the
largest model. Extraction transcribes a resume into a schema. The capability was
not being used — only its per-request latency was being paid.

**Change.** Run extraction on `gpt-5.4-mini`.

**Result.** Read against the floor table, not against the measured stage row:
median floor drops from 7.34s to 1.03s. The report's own note is explicit that
both arms ran extraction on the same model, so that row compares an identical
call with itself and should be read as run-to-run variance, not as the result.
**The model change is the change.**

Right-sizing per stage, rather than picking one model for the application, is
the durable lesson. Three of the four model-backed stages do not need the
largest model.

### 4. The planner's arithmetic — where latency was the wrong metric

**Symptom.** `scripts/run_intake.py` crashed on candidate_08 three attempts
running. The planner intermittently allocated competency question counts summing
to 9 instead of 10.

**Diagnosis.** An arithmetic slip, not a judgement call — and the model was
being asked to restate sums it had just produced, which is not what it is good
at.

**Change.** Send the allocation-relevant evidence fields only, derive
`difficulty_distribution` and `total_questions` in code, and give the planner a
bounded repair loop: show it its own rejected breakdown plus a directional
correction, then re-ask.

**Result. Latency got slightly worse: 4.86s → 5.47s, −12.5%.** Reliability went
from **7/10 to 10/10 successful plans.**

This is the most instructive entry in the document. A latency-only report would
have marked this change a regression and possibly reverted it. Three in ten
candidates hitting a validation failure is a far worse outcome than six hundred
milliseconds. The harness reports completion rate next to wall time precisely so
this trade is visible.

### 5. Question selection waited on retrieval it could have issued at once

**Symptom.** Stage 4 took 8.95s, most of it waiting.

**Diagnosis.** Every primary bucket's query is derivable from the plan alone.
The round trips were sequential for no reason other than code shape.

**Change.** Issue the primary retrievals concurrently; the sequential pass then
consumes the cache. Slot filling stays sequential on purpose — `used_ids`
deduplicates across slots, which makes bucket order part of the result.

**Result. 8.95s → 3.55s on candidate_14, with identical question IDs** — the
verification that mattered, since a faster selector returning different
questions would not have been the same function.
*(commit `a437804`)*

### 6. Extraction started later than it needed to

**Change.** Upload prefetch: extraction begins the moment a file lands, and the
result is *collected* rather than repeated when the button is clicked.

**Result.** The candidate spends their reading-and-clicking time in parallel
with stage 1 instead of before it. Structural, not measured in the report.

### 7. Retries were paying backoff for failures that could never succeed

**Symptom.** A billing-exhausted key took the SDK's full backoff before failing.

**Diagnosis.** Not all failures are alike. A 5xx, a dropped connection, or an
ordinary rate limit will plausibly succeed on retry. `insufficient_quota` will
not, ever.

**Change.** `src/llm_retry.py` classifies failures and fails terminal ones
immediately. It also retries a malformed structured-output parse, observed on
DeepSeek.

**Result.** Failures that cannot be fixed surface in seconds instead of after a
full backoff cycle. Worth noting this *removes* latency from the unhappy path,
which is the path a frustrated user is already on.

### 8. Two questions testing one idea — a quality bottleneck

**Symptom.** A ten-question interview could spend two slots on the same
knowledge. `AGENT-FUND-BAS-002` and `AGENT-FUND-INT-001` are inverse framings of
one trade-off: a candidate who knows either answers both. That pair consumed
20% of an interview on one decision framework.

**Diagnosis.** Deduplication was on `question_id` only.

**Change.** Compare each candidate question against every question already
accepted — not just the current slot, since the motivating pair sat in different
difficulty slots — on two signals already loaded from the corpus: shared
`sub_competency`, and must-have concept overlap above a threshold. No extra
retrieval, no model call.

Redundancy is treated as a *preference, not a rule*. An unfilled slot aborts the
whole intake, and some corpus pools hold a single question, so a flagged
question is deferred and admitted with a warning if no alternative exists.

**Result.** A plan allocating agentic_ai across two difficulties now resolves to
two distinct sub-competencies. Ten slots filled, no warnings.
*(commit `702a3d6`)*

Throughput was never the constraint here. Interview quality was.

### 9. Evaluation of ten answers

**Change.** `EvaluationAgent.evaluate_interview` submits each question to a
thread pool (default four workers) and reassembles results in frozen interview
order rather than completion order.

**Why it is safe.** Each question's evaluation is independent: its own
retrieval, its own assessment, its own terminal state. Nothing crosses between
them.

**Design constraint.** Evaluation only starts once the complete answer set
exists, so this parallelism is available by construction — a per-question
evaluation during the interview would have foreclosed it.

### 10. State that outlived what it belonged to (the UI era)

Three defects of one shape, found once the results screen existed:

- **Re-uploading a resume left the previous interview in session state.** Only
  the plan was replaced, so the traces view showed a fresh upload beside the
  finished answers and evaluation of the last run. A new plan now discards
  everything derived from the old one.
- **Generated HTML rendered as visible source.** Streamlit runs markdown before
  HTML, so four-space-indented markup became a fenced code block. Every builder
  is collapsed to one line, with a regression test.
- **In-form buttons were unstyled.** Streamlit names a form's submit button
  `primaryFormSubmit`, so an exact `button[kind="primary"]` selector silently
  skipped every call to action in the app.

All three share a root cause worth naming: **an assumption about framework
behaviour that was never verified against the running page.** Each was found by
loading the app in a browser and looking, not by reading the code.

---

## Part 4 — Cumulative effect

Intake stages 1–3, medians across five fixture resumes with repeats, measured on
`gpt-5.4`:

| | Baseline | Optimised | Change |
|---|---|---|---|
| Wall time | 16.27s | 11.64s | **−28.5%** |
| Model calls | 3 | 10 | +7 |
| Input tokens | 5,416 | 15,036 | +178% |
| Output tokens | 1,740 | 2,203 | +27% |
| Completion rate | 7/10 | **10/10** | +30pp |

Stage 4 is measured separately: **8.95s → 3.55s**.

The token columns are the honest cost of the fan-out. We spent tokens to buy
wall time and reliability, on a workload where a human is waiting.

---

## Part 5 — What these numbers do not say

Stated plainly, because a performance document that only reports wins is not
evidence of anything.

- **The report was produced on `gpt-5.4`, not the default model.** `gpt-5.6` was
  measurably degraded during the evaluation — 5.0–8.8s for a trivial call
  against ~1.0s on the smaller models, with repeated `InternalServerError`
  (503, "servers are currently overloaded"). A clean both-arms-on-`gpt-5.6`
  comparison could not be produced in that session. Provider-side variability is
  not something this work fixes or should be tuned around.
- **Extraction's stage row compares an identical call with itself.** Read it as
  the variance floor. The model change is the change.
- **A concurrent stage's slowest single call is its lower bound.** The gap above
  it is contention between overlapping calls, not measurement error.
- **Stage 4's figure is one candidate**, verified for identical output. It is
  not a distribution.
- **Evaluation and scoring have no equivalent latency study.** Their parallelism
  is structural and untimed. That is a gap, not a result.

---

## Part 6 — Still open

- No latency measurement exists for stages 6–7.
- The default model path has never been cleanly measured end to end; the numbers
  above describe a faster model than the one candidates hit by default.
- Retrieval refinement is not implemented: when evidence is thin the evaluation
  agent terminates as `NEEDS_REVIEW` rather than re-querying with a refined
  query.
- The learning catalog carries a cohort date and price that will age, with
  nothing to warn when they do.

---

## Sources

| Claim | Source |
|---|---|
| Per-stage intake timings, token counts, completion rate, model floor | `data/eval/intake_latency_report.json` |
| Measurement harness | `scripts/evaluate_intake_latency.py` |
| Question selection concurrency, gateway split, progressive render | commits `a437804`, `6dade8a` |
| Fan-out, model right-sizing, planner repair, retry classification | commit `105fad9` |
| Question redundancy | commit `702a3d6` |
| Full written account of the 2026-09-11 changes | `docs/CHANGES_2026-09-11.md` |
