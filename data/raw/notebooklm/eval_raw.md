## RAG Evaluation

### 1. Basic Question: Context Recall vs. Context Precision

**Question:** In a Retrieval-Augmented Generation (RAG) system, what is the practical difference between Context Recall and Context Precision? If your production traces show that the system frequently retrieves irrelevant chunks of text that distract the generation model, which metric is suffering, and what specific engineering action should you take to fix it?

**Grounded Answer Guidance:**

Context recall measures if the retrieved context contains all the needed evidence, while context precision measures if those retrieved chunks are actually useful and relevant. If irrelevant chunks are distracting the generator, context precision is low, and you should fix ranking/filtering (or add a reranker) rather than modifying the retrieval vector search directly.

### 2. Basic Question: Faithfulness vs. Response Relevancy

**Question:** Explain the distinction between Faithfulness (Groundedness) and Response Relevancy in a RAG pipeline. Is it possible for a generated response to be highly relevant to the user's prompt but fail a faithfulness check? Provide a brief scenario to illustrate this.

**Grounded Answer Guidance:**

Faithfulness checks whether the claims made in the answer are strictly supported by the retrieved context. Response relevancy checks whether the answer actually addresses the user's question. Yes, an answer can be highly relevant but unfaithful. For example, if a user asks "Can I return my order after 45 days?" and the bot confidently answers "Yes, you have a 45-day window," the response is highly relevant, but if the retrieved policy document states the limit is 30 days, the answer fails faithfulness (it is a hallucination).

### 3. Intermediate Question: Evaluating Abstention Ability

**Question:** You are evaluating a RAG-based customer support assistant and want to ensure it has a strong Abstention Ability (the capacity to say "I don't know" rather than fabricating an answer when evidence is missing). How would you construct a balanced evaluation dataset to measure this, and what does a "Pass" decision require for a given test case?

**Grounded Answer Guidance:**

You must construct a balanced evaluation set containing roughly equal parts of Answerable Questions (where correct, verifiable answers are present in the provided context) and Unanswerable Questions (queries about missing information or false premises designed to tempt hallucinations). A "Pass" requires the model to correctly answer the answerable questions while successfully refusing to answer the unanswerable ones.

### 4. Intermediate Question: RAG Pipeline Diagnosis

**Question:** During offline evaluations, you discover that your RAG pipeline has high Context Recall and high Context Precision, yet the Faithfulness of the generated responses is unacceptably low. What stage of your pipeline is failing, and what are the primary engineering steps you would take to resolve this issue?

**Grounded Answer Guidance:**

Since retrieval is working well (proven by high context recall and precision), the failure lies in the generation stage. To resolve this, you should focus on prompt engineering (such as adding stricter system prompt constraints regarding groundedness), tuning the model's parameters, or upgrading to a more capable model.

### 5. Advanced Question: Evaluator Validation and Bias Correction

**Question:** Jason Liu's RAG evaluation framework breaks down generation quality into three key relationships: C|Q, A|C, and A|Q. Explain what these represent. Furthermore, explain why you should validate an LLM-as-judge scoring these relationships against expert human annotations before using its scores to make shipping decisions, and how establishing the judge's true positive and true negative rates helps you correct your system's estimated failure rate.

**Grounded Answer Guidance:**

C|Q evaluates context relevance to the query; A|C evaluates answer faithfulness to the context; A|Q evaluates answer relevance to the query. You must validate the LLM judge because off-the-shelf evaluator prompts are prone to inherent biases and may not align with your specific domain's quality criteria. By calculating the True Positive Rate (TPR) and True Negative Rate (TNR) of the LLM judge on a human-annotated golden test set, you can mathematically correct the judge's estimates to determine the actual failure rate in your system.

## Metrics

### 1. Basic Question: Cost-Based Metric Optimization

**Question:** When evaluating an extraction or classification task, how do you use the "cost of failure" to decide whether to optimize for Precision or Recall? Give a real-world example of an AI application where you would maximize precision, and one where you would prioritize recall.

**Grounded Answer Guidance:**

If "false alarms" (false positives) are highly expensive or risky, you must optimize for precision. If missing a positive case (false negatives) is highly expensive, you must optimize for recall. For example, in a medical triage tool, missing a severe symptom is critical, so you prioritize recall. In a customer support auto-refund bot, triggering an accidental payout is expensive, so you prioritize precision.

### 2. Basic Question: Semantic Similarity vs. Structured Rubrics

**Question:** Why are traditional n-gram overlap metrics (like BLEU or ROUGE) often poor choices for evaluating open-ended natural language responses from LLMs? What alternative automated method is preferred for grading subjective qualities like brand compliance, tone, or style?

**Grounded Answer Guidance:**

BLEU and ROUGE measure exact word overlaps and are weak because they fail to capture meaning when many valid phrasings exist. For subjective qualities like tone or style, developers should prefer LLM-as-judge metrics utilizing clear, structured rubrics or binary brand compliance checks, which can capture semantic nuance.

### 3. Intermediate Question: Binary (Pass/Fail) vs. Likert Scales

**Question:** Many engineering teams default to using a 1-to-5 Likert scale for human and LLM evaluations. Outline three practical reasons why prominent evaluation experts advise using binary (Pass/Fail) evaluations instead. If you still need to track gradual, incremental improvements, how can you do so using binary checks?

**Grounded Answer Guidance:**

Likert scales introduce subjectivity (different annotators interpret 3 vs 4 differently), require larger sample sizes to detect statistical differences, and encourage annotators to select middle values to avoid hard decisions. To track gradual improvements, you should split the evaluation into specific sub-components with their own binary checks (e.g., tracking "4 out of 5 expected facts included" as separate binary checks).

### 4. Intermediate Question: Safe Repurposing of Generic Metrics

**Question:** Why is relying blindly on "ready-to-use" off-the-shelf evaluation metrics (like general helpfulness or coherence scores) considered a risk for production AI applications? How can these generic metrics be safely repurposed as "exploration signals" during development?

**Grounded Answer Guidance:**

Generic metrics measure abstract qualities that may not align with your specific application's goals, creating a false "illusion of confidence" while failing to catch domain-specific errors. However, they can be safely repurposed as exploration signals (or screening filters) to find outlier traces (extremely low or high scores) for humans to manually review during error analysis.

### 5. Advanced Question: Calibrating LLM-as-a-Judge and Handling Drift

**Question:** When building a custom LLM-as-a-judge to evaluate open-ended outputs, explain the structured process of calibrating it against human expert judgment. In your explanation, address: the role of Cohen's Kappa, how to mitigate the phenomenon of "criteria drift" during evaluation design, and how to structure the judge's output schema to prevent hallucinations or arbitrary scores.

**Grounded Answer Guidance:**

Calibration involves having humans score a gold set of 100-200 examples, running the LLM judge on the same set, and measuring agreement. Cohen's Kappa should be used to calculate inter-annotator agreement beyond chance. To handle criteria drift—where evaluation criteria shifts as you observe outputs—you must treat evaluation as an iterative, human-driven process of "open coding" and prompt tuning rather than a static setup. The output schema should use low-precision binary rules, enforce chain-of-thought reasoning before outputting the score, and provide a "way out" (like returning "Unknown") when there is insufficient information.

## Agentic Evaluation

### 1. Basic Question: Outcome vs. Trajectory (Transcript) Evaluation

**Question:** In agent evaluation, explain the difference between evaluating the Outcome of a trial versus evaluating its Trajectory (transcript or trace). Why is verifying the environmental outcome considered the ultimate gold standard of success?

**Grounded Answer Guidance:**

The trajectory is the complete multi-turn record of messages, reasoning, and tool calls. The outcome is the final state of the environment at the end of the run (e.g., whether a reservation actually exists in a SQL database). The outcome is the gold standard because agents can claim they succeeded in the transcript while failing to write to the database, or they can find creative, unscripted solutions in the environment that technically bypass the anticipated trajectory but still satisfy the user's goal.

### 2. Basic Question: Trajectory Match Modes

**Question:** You are testing an agent's execution path against a hard-coded reference trajectory using step-by-step match modes. In what specific scenarios would you choose Subset match mode over Superset match mode, and what is the primary structural goal of each?

**Grounded Answer Guidance:**

You choose Subset match mode to ensure agent efficiency by verifying that the agent did not call any irrelevant or unnecessary tools beyond the reference. You choose Superset mode when you want to verify that a minimum set of critical actions was taken, but you are okay with the agent calling additional tools.

### 3. Intermediate Question: pass@k vs. pass^k for Reliability

**Question:** Describe the two distinct metrics used to analyze agent success rates over multiple trials: pass@k and pass^k. Under what product requirements or user scenarios would you prioritize optimizing pass^k instead of pass@k?

**Grounded Answer Guidance:**

pass@k measures the likelihood that an agent gets at least one correct solution in k attempts (ideal for tools like code generation where a user can choose the best output). pass^k measures the probability that all k trials succeed. You prioritize pass^k for customer-facing or autonomous agents where consistency is essential and users expect reliable behavior every single time.

### 4. Intermediate Question: Diagnosing Hotspots with Transition Matrices

**Question:** What is a Transition Failure Matrix, and how can an AI engineer leverage it to identify specific performance bottlenecks in a multi-step, sequential agentic workflow (such as a text-to-SQL pipeline)?

**Grounded Answer Guidance:**

It is a matrix where rows represent the last successful state and columns represent where the first failure occurred. By plotting these transitions, engineers can quickly see "hotspots" where the workflow consistently breaks (e.g., transitioning from planning to SQL execution), allowing them to target debugging efforts where they will have the highest ROI.

### 5. Advanced Question: Multi-Turn Conversation Debugging

**Question:** When evaluating a complex, multi-turn conversational agent, outline the two-phase evaluation framework (E2E task success vs. step-level diagnostics). If your agent fails at turn 4 of a multi-turn conversation, explain the practical debugging strategy of simplifying it to a "single-turn" baseline and using "N-1 testing" with real conversation prefixes to isolate the issue.

**Grounded Answer Guidance:**

The framework starts with Phase 1: evaluating end-to-end task success (treating the agent as a black box). Once failure areas are identified, you move to Phase 2: step-level diagnostics (evaluating tool choice, parameter extraction, and context retention). If a failure occurs on turn 4, you simplify it to a single-turn query to see if it still fails; if it does, the issue is basic retrieval or knowledge, not conversational history. If it passes, you use N-1 testing, providing the first 3 turns of a real conversation prefix and testing the agent's behavior on turn 4 to isolate the multi-turn context failure.

## Cost and Latency

### 1. Basic Question: Time to First Token (TTFT)

**Question:** When evaluating the speed of a streaming conversational agent, what is Time to First Token (TTFT)? Why is TTFT often a more critical driver of user satisfaction than the total end-to-end response time [4, Page 118]?

**Grounded Answer Guidance:**

TTFT is the latency on the wall clock before the first token is displayed to the user [4, Page 118]. It is critical because it is the only speed metric users actually feel at the start of an interaction; streaming tokens can hide a slow overall generation rate, but nothing can hide a slow TTFT [4, Page 118].

### 2. Basic Question: Cost per Successful Task

**Question:** Why is tracking the raw token cost of a single, isolated agent run insufficient for calculating the actual production operating costs of an agentic system [4, Page 117]? Explain how the Cost per successful task metric accounts for retry and repair loops, and why a low task success rate heavily compounds your compute costs [4, Page 117, 490].

**Grounded Answer Guidance:**

Agents often fail and run retry or self-repair loops [4, Page 117]. A task that fails twice runs the entire stack (retrieval, reasoning, tools, and evaluation) three times before succeeding [4, Page 117]. Cost per successful task is calculated as the sum of all run costs divided by the success rate [4, Page 117, 490]. A success rate of 50% effectively doubles your real-world production costs [4, Page 117].

### 3. Intermediate Question: Latency Bottleneck Profiling

**Question:** An agentic pipeline consists of several sequential operations: Retrieval, Reranking, Tool Call, LLM thinking (TTFT), and Token Streaming [4, Page 118]. If users complain about slow responses, how would you systematically profile these "wall clock" steps to pinpoint the latency bottleneck [4, Page 118]?

**Grounded Answer Guidance:**

You must profile and log the duration of each distinct operation on the wall clock: measuring retrieval times (embedding + vector search), reranking latency, external tool execution (which are often "wild cards" in timing), TTFT, and the final streaming output rate (tokens per second) [4, Page 118]. This isolation shows which step compounds the latency most severely [4, Page 118].

### 4. Intermediate Question: Scaffolding-Level Cost Controls

**Question:** Besides changing the primary LLM, detail three distinct Agent Cost Control mechanisms that you can implement in the agent scaffold or harness to prevent runaway iteration loops and optimize token spend [4, Page 119].

**Grounded Answer Guidance:**

Scaffolding cost controls include: capping max steps (setting a hard ceiling on iterations), setting strict retry budgets (limiting retries per tool failure), employing prompt caching (reusing cached history and tool results), and implementing conversation summarization to compress the history context [4, Page 119].

### 5. Advanced Question: The Agent Evaluation Triangle

**Question:** Explain the three competing trade-offs represented by the "Agent Evaluation Triangle" (Accurate, Affordable, Fast) [4, Page 121]. Analyze how implementing a heavy, multi-turn LLM-as-judge online evaluator impacts overall system overhead, and propose a hybrid strategy that combines deterministic checks, sampling rates, and human annotation queues to maintain a balanced, cost-effective production monitoring stack.

**Grounded Answer Guidance:**

The triangle represents that agent systems must be accurate, affordable, and fast, but optimizing for one often compromises the others [4, Page 121]. Running multi-turn LLM judges on every production trace is highly accurate but creates massive token cost overhead and latency. A hybrid strategy mitigates this by:

- Running fast, cheap, deterministic code-based checks first (schema validation, format checks).

- Using sampling rates (e.g., evaluating only 5% of production traces or targeting traces with negative user feedback) to control judge costs.

- Routing ambiguous, high-stakes, or low-confidence traces to human Annotation Queues for expert triage and calibration.
