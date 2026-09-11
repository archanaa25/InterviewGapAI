is it more of deterministic workflow or is Interview Agent and EValuation Agent ?

Your overall system is mostly a deterministic workflow, with two bounded agentic components—if you implement the Interview Agent and Evaluation Agent with the decision loops we discussed.

I would describe InterviewGapAI as:

A deterministic AI workflow with bounded agentic decision-making at question selection and answer evaluation.

Not as a fully autonomous multi-agent system.

How I would classify each stage
Component	Classification
Resume Extractor	Deterministic workflow + structured LLM
Resume Analyzer	Bounded LLM reasoning
Interview Planner	Bounded LLM reasoning + deterministic validation
Question RAG	Retrieval tool
Interview Agent	Bounded Agent
Evaluation RAG	Retrieval tool
Evaluation Agent	Bounded Agent if implemented with decision/retrieval/validation loop
Competency aggregation	Deterministic
Skill-gap calculation	Deterministic

The architecture is therefore roughly:

                DETERMINISTIC / BOUNDED WORKFLOW
                           │
Resume → Extract → Analyze → Plan
                           │
                           ▼
                 ┌──────────────────┐
                 │ INTERVIEW AGENT  │  ← AGENTIC
                 │                  │
                 │ decide           │
                 │   ↓              │
                 │ Question RAG     │  ← TOOL
                 │   ↓              │
                 │ observe          │
                 │   ↓              │
                 │ accept/reject    │
                 │   ↓              │
                 │ retry/validate   │
                 └────────┬─────────┘
                          ↓
                    10 Questions
                          ↓
                  Candidate Answers
                          ↓
                 ┌──────────────────┐
                 │ EVALUATION AGENT │  ← AGENTIC
                 │                  │
                 │ assess           │
                 │   ↓              │
                 │ need knowledge?  │
                 │   ↓              │
                 │ Evaluation RAG   │  ← TOOL
                 │   ↓              │
                 │ evaluate         │
                 │   ↓              │
                 │ validate/revise  │
                 └────────┬─────────┘
                          ↓
                 Question Evaluations
                          ↓
                Deterministic Aggregate
                          ↓
                     Skill Gaps
When is the Interview Agent actually an agent?

If your teammate implements:

results = question_rag.search(...)
selected = results[0]

then no, that's just retrieval + deterministic selection.

But if it does:

Goal: satisfy interview plan
       ↓
Retrieve candidates
       ↓
Inspect results
       ↓
Decide accept/reject
       ↓
Too similar? → retrieve again
       ↓
Coverage poor? → replace question
       ↓
Validate final 10
       ↓
Repair if necessary
       ↓
Stop

then it is legitimately a bounded agent.

It has goal-directed behavior, tool use, observation, decision-making, state, iteration, and stopping criteria.

Same distinction for Evaluation Agent

If it simply does:

Evaluation RAG → LLM → score

I'd call it a RAG evaluation chain, not an agent.

If it does:

Inspect answer
      ↓
Can I evaluate confidently?
   ↙        ↘
 YES        NO
  ↓          ↓
evaluate    identify missing evidence
             ↓
         call Evaluation RAG
             ↓
         inspect evidence
             ↓
         sufficient?
          ↙      ↘
        YES      NO
         ↓        ↓
      evaluate   refine/retrieve
         ↓
      self-check
         ↓
      unsupported?
       ↙      ↘
     YES      NO
      ↓        ↓
 revise      finish

then yes, that's an Evaluation Agent.

And this is actually a better design

I wouldn't try to make the whole application agentic.

For example, there's no reason an agent should decide:

"Should I extract this resume next?"

The answer is predetermined.

Similarly:

10 question evaluations
        ↓
average/weighted competency score

doesn't need an agent.

Your own MINT-oriented design philosophy supports using the simplest reliable mechanism for each stage.

So for your presentation, I would avoid saying:

"InterviewGapAI is a multi-agent system."

Instead:

"InterviewGapAI is a controlled AI workflow that combines deterministic orchestration, two specialized RAG systems, and bounded agents where iterative reasoning and tool use add value."

That is technically more accurate—and makes the architectural choices easier to defend if your mentors ask, "Why did this need to be an agent?"