# InterviewGapAI --- Project Status Checkpoint

**Current status:** Question RAG finalized; next phase is Candidate
Resume → Resume Analysis → Interview Plan.

## Project Goal

InterviewGapAI identifies demonstrated AI Engineer skill gaps rather
than treating skills missing from a resume as missing knowledge. Missing
resume evidence is treated as **unknown / needs probing**, not
automatically as weakness.

## Corpus

-   112 curated interview questions
-   35 evaluation-knowledge records
-   Competencies: RAG, Agentic AI, AI/ML/LLM Fundamentals, AI
    Evaluation, Python/Software Engineering, AI System Design, AI
    Security

Prepared master corpus:

``` text
data/prepared/master/
├── interview_questions.jsonl
├── evaluation_knowledge.jsonl
└── corpus_manifest.json
```

## Golden Retrieval Dataset

50 queries covering semantic, keyword, scenario, cross-concept,
hard-semantic, ambiguous, near-neighbor/confusable, and
negative/out-of-scope cases.

## Question RAG Experiments

  -------------------------------------------------------------------------------
  Experiment         Recall@1     Recall@5          MRR       NDCG@5      Approx.
                                                                          Latency
  -------------- ------------ ------------ ------------ ------------ ------------
  BM25                 0.6630       0.8259       0.7711       0.7658     \~0.4 ms

  Dense                0.6852       0.9315       0.8193       0.8366     \~709 ms

  Hybrid RRF           0.7204       0.8741       0.8304       0.8212     \~758 ms

  Dense +              0.7074   **0.9593**       0.8563       0.8692     \~724 ms
  Competency

  Dense +          **0.7963**       0.9481   **0.9130**   **0.9047**     observed
  Competency +                                                          \~2223 ms
  Difficulty

  Dense + Full         0.8926       0.9481       0.9741       0.9476     \~761 ms
  Metadata
  -------------------------------------------------------------------------------

## Selected Question RAG

**OpenAI embeddings + Pinecone Dense Retrieval filtered by competency +
difficulty.**

Why: - Competency and difficulty naturally come from the Interview
Plan. - Recall@1 = 0.7963 - Recall@5 = 0.9481 - MRR = 0.9130 - NDCG@5 =
0.9047 - Hybrid RRF was evaluated but reduced Recall@5. - Full
sub-competency filtering was not selected because it can make retrieval
unrealistically easy.

**Question RAG is frozen for the 3-day MVP.**

## Product Architecture

The overall workflow is deterministic, with bounded AI/agentic reasoning
where useful.

``` text
JD + Candidate Resume
        ↓
Pre-Interview Analysis
        ↓
Interview Plan
        ↓
Interview Agent
        ↓
Question RAG
        ↓
Freeze 10 Questions
        ↓
One-Question-at-a-Time Streamlit UI
        ↓
Submit All Answers
        ↓
Evaluation Agent
        ↓
Evaluation RAG
        ↓
Per-Question Evaluation
        ↓
Competency Aggregation
        ↓
Skill Gap Analysis
        ↓
Learning Recommendations
```

### Interview Agent

Goal: construct a balanced 10-question interview satisfying competency
and difficulty targets, using Question RAG and avoiding
duplicates/excessive overlap.

### Evaluation Agent

Goal: assess demonstrated competency using Evaluation RAG, expected
concepts and candidate answers, producing structured scores, strengths
and missing concepts.

## Interview Design

The MVP interview is **not adaptive**. Ten questions are selected and
frozen before the interview. Streamlit shows one question at a time.
Evaluation occurs after final submission, not after each Next click.

## State

Use `st.session_state` for the active interview: - resume analysis -
interview plan - selected questions - current question index - answers -
interview status - evaluation results

This is application state, not long-term agent memory.

For Plan B, use SQLite for completed interview history and analytics.

## Plan A --- Candidate-Only MVP

Flow:

``` text
Resume → Analysis → Interview Plan → Interview Agent + Question RAG
→ 10 Questions → Q1...Q10 → Submit
→ Evaluation Agent + Evaluation RAG
→ Scores → Gaps → Learning Recommendations
```

Streamlit views: 1. Setup / Resume Upload 2. Interview Ready 3.
One-Question-at-a-Time Interview 4. Results

No roles, authentication, analytics or candidate comparison required.

## Plan B --- Candidate + Interviewer

Reuses the same AI core.

Candidate: - My Interview - My Results

Interviewer: - Dashboard - Candidates - Interview Results

Dashboard can show: - interviews completed - average score - candidate
comparison - competency averages - candidate drill-down - question-level
evaluation - strengths and gaps

Use SQLite for persistence. For the demo, a simple Candidate/Interviewer
role selector is enough; production authentication is deferred.

## Deferred Features

-   adaptive interviewing
-   dynamic difficulty
-   real-time per-answer evaluation
-   Mem0/vector/long-term conversational memory
-   multi-agent supervisor
-   more RRF/reranking optimization
-   production OAuth/SSO and complex RBAC
-   dedicated Learning Agent
-   semantic analytics over historical candidates

## 3-Day Implementation Plan

### Day 1 --- Interview Preparation

``` text
Resume → Resume Analysis → Interview Plan
→ Interview Agent → Question RAG → Freeze 10 Questions
```

### Day 2 --- Complete Plan A

``` text
One-question UI → 10 Answers → Evaluation Agent
→ Evaluation RAG → Per-question Scores
→ Competency Aggregation → Skill Gap Report
→ Learning Recommendations
```

**Plan A must be fully demoable by end of Day 2.**

### Day 3 --- Stabilize, Then Extend

First: end-to-end testing, guardrails, UI polish, error handling and
demo data.

Only if Plan A is stable: SQLite, role selector, interviewer dashboard,
history and candidate comparison.

## Immediate Next Step

Question RAG is complete. Next:

``` text
Candidate Resume → Resume Analysis → Interview Plan
```

Start with about 5 controlled synthetic resumes: 1. Strong overall AI
Engineer 2. Strong RAG, limited Agentic AI evidence 3. Strong Agentic
AI, limited RAG evidence 4. Strong Software Engineer transitioning to
GenAI 5. Resume omits several skills the candidate may actually know

Before generating them, define: - Candidate Resume schema - Resume
Analysis output schema - Interview Plan schema
