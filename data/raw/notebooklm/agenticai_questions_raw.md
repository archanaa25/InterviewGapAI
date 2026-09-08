## SUB-COMPETENCY 1: agent_fundamentals — AI Agents, Agentic Considerations, Use Cases

### Question 1.1 (Basic)

How does an AI agent differ conceptually from a traditional chatbot and a deterministic workflow?

**Concise Grounded Answer / Grading Guide:**

- **Chatbot:** Operates in a single turn; it answers a user prompt and immediately stops without an observation-reasoning loop1.

- **Deterministic Workflow:** Follows a predefined, hardcoded path where the control graph is designed by the developer at build time1. The LLM generates outputs at specific nodes but never decides the execution route itself1.

- **AI Agent:** A goal-driven system that uses an internal loop (think $\rightarrow$ act $\rightarrow$ observe) to dynamically decide its own next steps and tool execution at runtime1more_horiz.

### Question 1.2 (Basic)

What are the three primary system properties or task characteristics that justify moving from a simpler workflow to a fully autonomous AI agent?

**Concise Grounded Answer / Grading Guide:**

- **Unknown Path:** When the next step depends entirely on what the previous step returned, making it impossible to hardcode a static decision tree1.

- **High Variance Input:** When inputs have hundreds of different shapes/structures that would break a rigid, handcoded graph1.

- **Long-Horizon Tasks:** When tasks exceed 10+ steps with multiple retry branches, where writing every possible code branch manually is impractical1.

### Question 1.3 (Intermediate)

Under what conditions or operational constraints are deterministic workflows preferred over agentic workflows? Give three concrete scenarios.

**Concise Grounded Answer / Grading Guide:**

Traditional deterministic workflows outperform agents in:

- **Predictable processes:** When steps are known and fixed in advance (e.g., onboarding flow, invoice processing, content moderation)14.

- **Strict compliance/auditable flows:** When regulations demand a guaranteed audit trail and fixed code paths rather than model-driven decisions (e.g., KYC, GDPR requests, SOC 2 controls)1.

- **High-volume/low-variance operations:** When running tasks millions of times a day and per-call cost/latency compound, allowing caching, batching, and routing to cheap models (e.g., email categorization, log triage)1.

### Question 1.4 (Intermediate)

Explain how "autonomy" behaves as a spectrum rather than a binary switch. What are the four levels of autonomy defined in agentic design?

**Concise Grounded Answer / Grading Guide:**

Autonomy is a progressive spectrum where trust requirements, eval rigor, and the cost of failure grow as you move up the ladder1:

- **Level 1 (Suggest):** Model writes suggestions; the human must approve every single action before execution (e.g., GitHub Copilot)1.

- **Level 2 (Act with approval):** Model proposes a batch of actions, and the human reviews and clicks "run" to authorize the batch1.

- **Level 3 (Act, ask on risk):** Model autonomously executes safe/read-only actions but pauses to ask the human only for high-risk, irreversible, or expensive operations1.

- **Level 4 (Fully autonomous):** Model runs end-to-end to completion without human intervention during execution, and the human performs a retrospective audit1.

### Question 1.5 (Advanced)

As you move an AI agent from low autonomy (like a Q&A assistant) to high autonomy (such as an autonomous coding agent operating in a sandbox), what architectural guardrails, evaluation rigor, and monitoring capabilities must scale to maintain safety?

**Concise Grounded Answer / Grading Guide:**

Moving up the autonomy and control grid introduces severe risks of cascading errors and silent failures1. Candidates must outline how the following layers must scale:

- **Control / Guardrails:** Scaling from basic accept/reject toggles to multi-layered guardrails (e.g., sandboxes, tool call allowlists, scoped permissions, spend caps, and kill-switches) to block malicious/hallucinated writes1.

- **Evaluation Rigor:** Transitioning from simple thumb-up user feedback to robust, offline regression testing, golden datasets, trajectory-based evals, and automated LLM-as-a-judge simulators1more_horiz.

- **Observability:** Moving from minimal/no logging to comprehensive production tracing (capturing every tool call, latency, step-by-step reasoning plan, and cost tracking)17.

- **Recovery:** Moving from simple human retries to auto-retry logic with exponential backoff, fallback models, and programmatic escalation paths1.

## SUB-COMPETENCY 2: agent_state_memory — Memory and State

### Question 2.1 (Basic)

What is the fundamental architectural difference between an agent's "State" and an agent's "Memory"?

**Concise Grounded Answer / Grading Guide:**

- **State (or Task State):** It is per-task, ephemeral, and session-scoped18. It serves as the agent's working notebook for the current run, tracking task progress, intermediate tool results, and upcoming actions1. It is lost when the current context resets8.

- **Memory:** It is cross-task and persistent across sessions and users18. It stores long-term information, user preferences, and learned patterns that survive context window resets18.

### Question 2.2 (Basic)

Differentiate between "Episodic Memory" and "Semantic Memory" in AI agents, including how their life cycles and storage methods differ.

**Concise Grounded Answer / Grading Guide:**

- **Semantic Memory:** Represents "what is true"8. It contains stable, atemporal facts, preferences, and system guidelines (e.g., user preferences or codebase facts)18. It has a long life cycle and is typically stored in key-value stores or vector databases, only updating when directly contradicted18.

- **Episodic Memory:** Represents "what happened"8. It contains time-indexed, specific historical events and prior run logs (e.g., "refunded ORD-8392 on May 24")18. Its lifecycle involves natural decay, archiving, or compression, and it is retrieved to provide historical context18.

### Question 2.3 (Intermediate)

Explain the trade-offs of the following memory storage backends: Conversation Summary, Vector Store, and Key-Value Store. Which is best suited for user preferences, and which for long context summaries?

**Concise Grounded Answer / Grading Guide:**

- **Conversation Summary:** Compresses older conversational turns to fit within a bounded context window8. Trade-off: Slows down context bloat but sacrifices exact conversational details and reasoning trails8. Best for long context-window-bound sessions8.

- **Vector Store:** Stores text chunks as embeddings and retrieves them using cosine similarity8. Trade-off: Highly scalable for huge corpora but prone to retrieving out-of-context or semantically mismatched information8. Best for semantic search and project knowledge bases8.

- **Key-Value Store:** Stores simple {key: value} pairs retrieved directly by ID8. Trade-off: Extremely fast and deterministic but cannot handle unstructured, multi-dimensional query relationships8. Best for user preferences and fast session state8.

### Question 2.4 (Intermediate)

What are the four major architectural anti-patterns of agent memory design? For each, propose a corresponding engineering fix.

**Concise Grounded Answer / Grading Guide:**

- **Anti-pattern 1: Save Everything:** Storing every raw conversation turn, causing the database to bloat and retrieval to slow down8. Fix: Be selective at write-time, extracting only high-signal facts and discarding the chatter8.

- **Anti-pattern 2: Retrieve Everything:** Flooding the context window with marginally relevant documents8. Fix: Start with a low top-k retrieve (e.g., $k=3$), apply confidence thresholds, and use a re-ranking model to filter out noise8.

- **Anti-pattern 3: Chat History = Memory:** Conflating the scrolling UI transcript with a queryable, durable memory store8. Fix: Decouple them; use a separate extraction pipeline to feed durable memory and query it selectively8.

- **Anti-pattern 4: No Evals for Memory:** Failing to measure if retrieval is helping or hurting task success8. Fix: Build memory evals to check if retrieved facts are correct and if the model utilizes them successfully8.

### Question 2.5 (Advanced)

Design a memory write and retrieval pipeline for a multi-session Customer Support agent that complies with strict privacy standards (like GDPR / PII redaction) and prevents the risk of "stale memory" (context drift over time).

**Concise Grounded Answer / Grading Guide:**

A robust production-ready memory pipeline must implement:

- **PII and Secrets Redaction Layer:** Run a dedicated redaction/tokenization filter on any conversational turn before writing to vector or key-value stores to ensure auth tokens, passwords, and PII are stripped8.

- **Write Sensitivity Gating:** Save routine preferences automatically, but implement an "Ask First" consent prompt for highly sensitive data (e.g., financial or healthcare inputs)8.

- **Stale Memory Prevention (Timestamp & Decay):** Attach metadata (created_at and last_confirmed_at) to every stored fact8. Set decay lifecycles so that preferences expire after a defined period (e.g., weeks)8.

- **Contradiction Management ("Contradiction Wins"):** When a retrieved memory directly conflicts with a newer user input, the pipeline must overwrite/archive the old fact with the updated one rather than keeping both8.

- **Action Verification:** On high-stakes actions, trigger a "Confirm before acting" check to re-verify the stale memory instead of blindly trusting it8.

## SUB-COMPETENCY 3: agent_design_patterns — Agent Design Patterns, Single vs Multi-Agent

### Question 3.1 (Basic)

Briefly explain the difference between the "Supervisor" pattern and the "Reflection" pattern in multi-agent orchestration.

**Concise Grounded Answer / Grading Guide:**

- **Supervisor Pattern:** A central coordinator agent (the supervisor) dynamically decomposes a task, delegates specific subtasks to specialized worker agents at runtime, and synthesizes the outputs19.

- **Reflection Pattern:** Consists of a Generator agent and a Reflector (Evaluator) agent19. The Generator drafts an output, and the Reflector critiques it against criteria in a feedback loop19. The loop repeats until the criteria are satisfied or a max-iteration limit is hit19.

### Question 3.2 (Basic)

What are the core limitations of a "Single-Agent" architecture that drive developers to adopt "Multi-Agent" pipelines?

**Concise Grounded Answer / Grading Guide:**

Single agents manage planning, tools, and reasoning in a single context window1. They break because:

- **Context Window Exhaustion:** The context window quickly explodes with raw tool outputs and historical chatter110.

- **Prompt Bloat:** Combining all instructions and tool descriptions into one prompt degrades model accuracy111.

- **Error Contamination:** An error or hallucination in an early reasoning step contaminates the entire context, causing downstream steps to fail112.

### Question 3.3 (Intermediate)

When designing a multi-agent system, how do the "Planner-Executor" and "Router" architectures manage computational costs and latency differently?

**Concise Grounded Answer / Grading Guide:**

- **Planner-Executor:** Splitting the thinking from the doing reduces costs19. An expensive, strong model runs once upfront to generate a multi-step plan19. A cheaper, faster model then executes the planned steps sequentially without needing to replan at every turn19. Re-planning only occurs upon unexpected tool failures or surprises19.

- **Router Pattern:** Uses a small, cheap classifier (the router) to inspect the incoming request and dispatch it directly to a single, highly specialized workflow, tool, or specialized model (e.g., Haiku for FAQs, Opus for deep reasoning)1more_horiz. This avoids invoking an expensive orchestration loop for simple tasks1.

### Question 3.4 (Intermediate)

Describe three common failure modes unique to "Multi-Agent" systems and explain how to mitigate them.

**Concise Grounded Answer / Grading Guide:**

- **Duplicated Work:** Multiple parallel agents independently solve the same sub-task, doubling token costs14. Mitigation: Implement a centralized task store/ledger where agents must trace and claim a task ID before starting14.

- **Cascading Errors:** Downstream agents blindly trust and build upon incorrect or hallucinated outputs from upstream agents1415. Mitigation: Enforce output verification checks and pass confidence scores alongside handoff payloads14.

- **Runaway Loops (Infinite ping-pong):** Agents get stuck repeatedly asking each other for clarification or help14. Mitigation: Enforce a global monitor that tracks total multi-agent turns, wall-clock time, and halts the execution on breach1416.

### Question 3.5 (Advanced)

Anthropic’s production "Research" system uses a multi-agent orchestrator-worker pipeline. Explain how this architecture distributes context windows, scales token budgets to maximize performance, and manages the "game of telephone" during handoffs.

**Concise Grounded Answer / Grading Guide:**

- **Context Window Distribution:** Instead of a single agent holding the entire search history, a Lead Researcher agent coordinates and spawns parallel subagents1718. Subagents operate with clean, independent context windows to search the web, acting as filters that condense raw tokens before returning high-signal findings to the lead19.

- **Scaling Token Budgets:** Multi-agent systems scale performance because performance is highly correlated with the volume of tokens processed (explaining 80% of variance on benchmarks like BrowseComp)20. Parallel subagents allow the system to spend more tokens on reasoning, bypassing the capacity constraints of a single agent20.

- **Game of Telephone Mitigation (Filesystem Artifacts):** During handoffs, passing full conversation transcripts bloats context windows and degrades quality21. To prevent this, subagents compile detailed reports and output them directly to an external filesystem, passing only a lightweight reference/pointer back to the Lead Researcher21. This keeps handoff payloads small and avoids loss of fidelity21.

## SUB-COMPETENCY 4: human_in_the_loop — Human-in-the-Loop and approvals

### Question 4.1 (Basic)

Why is Human-in-the-Loop (HITL) considered a "non-negotiable" feature for enterprise agent deployment? What are two distinct business benefits?

**Concise Grounded Answer / Grading Guide:**

Q&A bots and simple workflows can run autonomously, but complex agents that make real-world state changes often fail security, legal, or procurement audits without HITL1.

- **Benefit 1: Risk Mitigation and Compliance:** Ensures compliance with strict regulations (e.g., EU AI Act Art. 14) and prevents catastrophic mistakes (unapproved payment transfers, contract edits) from hitting production directly1.

- **Benefit 2: Review as Training Data:** Captures high-quality, real-world human corrections, rejections, and labels, which serve as invaluable datasets for subsequent model fine-tuning and regression evaluations22.

### Question 4.2 (Basic)

List four critical locations in an agentic control flow where human checkpoints should be explicitly placed.

**Concise Grounded Answer / Grading Guide:**

Human checkpoints must be placed22:

- **Before external actions:** Anytime a call leaves the system (e.g., sending emails, publishing Slack posts, executing payments)22.

- **Before customer-facing outputs:** Preventing hallucinations from reaching clients22.

- **After low-confidence retrieval/reasoning:** When the agent's confidence falls below an acceptable threshold22.

- **Before irreversible operations:** Destructive tool actions (e.g., dropping database tables, deleting accounts)22.

### Question 4.3 (Intermediate)

Explain how to design a "Confidence Threshold" logic system to handle agent output. Define the boundaries for the "Proceed", "Confirm", and "Stop" actions.

**Concise Grounded Answer / Grading Guide:**

A classifier or model-reported confidence score determines the action route22:

- **Proceed (e.g., Score > 0.85):** Agent autonomously executes the tool call, logs the trace, and moves on22. Best for strong evidence and low-risk, fully reversible actions22.

- **Confirm (e.g., 0.60 to 0.85):** Agent drafts the action but pauses execution, surfacing a review interface for a human to check and click "run"22. Best for medium confidence or customer-facing outputs22.

- **Stop (e.g., Score < 0.60):** Agent halts immediately, refuses to act, and escalates to a human with a clear handoff (e.g., "I am not sure, handing off")22. Best for repeated failures or extremely weak retrieval22.

### Question 4.4 (Intermediate)

What are three common human-in-the-loop design anti-patterns that lead to reviewer burnout? How do you solve them?

**Concise Grounded Answer / Grading Guide:**

Reviewer burnout is a major cause of agent deployment failure22:

- **Anti-pattern 1: Review Everything:** Routing 100% of outputs to human review, causing "rubber-stamping"22. Fix: Route only high-stakes or low-confidence items22.

- **Anti-pattern 2: Hide Source Evidence:** Presenting the agent's drafted action but hiding the actual sources or documents it read22. Fix: Directly link and highlight every claim to the source passages/files22.

- **Anti-pattern 3: Alert Fatigue:** Marking every review ticket as urgent22. Fix: Implement a multi-tiered priority system (max 3 tiers) and allow auto-escalation22.

### Question 4.5 (Advanced)

Suppose you are designing a Human-in-the-Loop review queue interface for a Billing Refund Agent. Detail the six specific components of state information the interface must surface to the human reviewer to allow them to make an informed, rapid decision.

**Concise Grounded Answer / Grading Guide:**

The reviewer requires a comprehensive "State Handoff" to make a decision without researching from scratch22:

1. **Task Context:** What is the specific goal? (e.g., "Process refund request of $240 for Customer #8821")22.

2. **Recommended Action:** What does the agent want to do? (e.g., "Issue full refund of $240 back to original Visa card")22.

3. **Reasoning Summary:** A concise natural language explanation of the agent's logic (e.g., "Shipped 18 days ago. Damaged on arrival. Refund threshold is under $500")22.

4. **Evidence & Sources:** Direct links to the files, PDF invoices, or Zendesk attachments the agent used to verify the claim22.

5. **Tool Calls (collapsed/inspectable):** What APIs did the agent execute during the run? (e.g., get_order(), check_refund_policy())22.

6. **Confidence Score:** The exact numeric score and threshold indicator (e.g., "0.91 confidence, threshold is 0.85")22.

## SUB-COMPETENCY 5: agent_reliability — Failure Modes, Cost, Latency and Reliability

### Question 5.1 (Basic)

What is the "compound error rate" problem in long-horizon agents? If an agent has a 95% success rate per step, what is its expected success rate across a 6-step task chain?

**Concise Grounded Answer / Grading Guide:**

- **Concept:** In an agentic loop, errors compound exponentially across steps1. A minor mistake in step 1 cascades, causing the model's environment observations to drift, leading to a much higher failure rate at completion123.

- **Calculation:** Expected end-to-end success rate = $0.95^6 \approx 73.5\%$1.

### Question 5.2 (Basic)

Why does an agent stuck in an infinite loop cause a quadratic explosion in token cost, and how can prompt caching mitigate this?

**Concise Grounded Answer / Grading Guide:**

- **Quadratic Cost:** During a loop, the agent resends the entire conversation history, including all prior tool calls and observations, at every new turn24. The prompt size grows quadratically, consuming enormous token volumes2425.

- **Prompt Caching Mitigation:** Since new turns are appended to the end of the existing prompt, the old prompt serves as an exact prefix26. Reusing the prefix computation via prompt caching keeps the model's actual inference computation linear rather than quadratic, dramatically cutting costs26. Note that prefix consistency must be strictly maintained (e.g., listing tools in the exact same order) to avoid breaking the cache26.

### Question 5.3 (Intermediate)

Explain five specific methods an AI Engineer can implement to reduce the runtime costs of a complex, long-running agent.

**Concise Grounded Answer / Grading Guide:**

Candidates should list at least five of the following:

- **Use smaller models for simple steps:** Route tasks like extraction, formatting, and simple classification to cheap models (e.g., Haiku) and save frontier models (e.g., Opus) for reasoning113.

- **Cache repeated work:** Maximize prompt caching and retrieval caching126.

- **Limit Retries:** Cap retries on API errors (e.g., max 3) to prevent runaway loops1.

- **Cap Maximum Steps:** Force a hard stop condition on execution length127.

- **Separate Planner from Executor:** Use an expensive model once for planning, and a fast, cheap model to execute the subtasks19.

- **Batch Requests:** Process multiple independent operations in parallel batches1.

### Question 5.4 (Intermediate)

Describe the "Latency Reduction Playbook" for agents. What are four strategies to decrease perceived and actual latency?

**Concise Grounded Answer / Grading Guide:**

- **Parallel Tool Calls:** Execute multiple independent API or search queries concurrently instead of waiting for each sequentially (Anthropic's Research cut time by 90% using this)128.

- **Streaming Responses:** Stream the model's output in real time so the user perceives immediate progress before generation completes1.

- **Prefetching:** Proactively load likely-needed data (like episodic memory or project files) in the background before the agent explicitly queries it1.

- **Simpler Routing:** Strip away unnecessary model-to-model delegation steps; a flatter control flow is faster1.

### Question 5.5 (Advanced)

Design a "Reliability Guardrail Stack" for safe tool execution. Explain how you would prevent a model from calling a destructive tool with hallucinated parameters or executing a payment transfer via prompt injection.

**Concise Grounded Answer / Grading Guide:**

A robust tool execution guardrail stack must implement the following sequential filters before code runs on the server1:

1. **Allowlist Check:** Verify the proposed tool name is registered in the current active agent's allowlist (catches hallucinated tools)1.

2. **Schema Validation:** Force strict JSON schema parsing to validate parameter types, enums, and required fields129.

3. **Scoped Permissions:** Check if the active session/user has authorization to execute this specific action (prevents cross-tenant access)1.

4. **Read vs. Write Split:** Flag any write operations as high-risk, segregating safe read-only queries1.

5. **Confirmation Step:** Interpose a human-in-the-loop checkpoint for any irreversible action (deletions, financial transfers)122.

6. **Sandbox Isolation:** Run all code execution or shell tools in a secure, isolated container sandbox with no access to the host network1.

## SUB-COMPETENCY 6: agent_lifecycle — ADLC and MINT Framework

### Question 6.1 (Basic)

Outline the six stages of the Agent Development Lifecycle (ADLC).

**Concise Grounded Answer / Grading Guide:**

The ADLC consists of1:

0. **Scope:** Define the user task, agent boundaries, allowed actions, success metrics, and failure cases (Start with the problem, not the model)1.

1. **Prototype:** Explore workflows rapidly using draft prompts, sample inputs, and basic tool testing1.

2. **Build:** Construct the working system, establishing prompts, tools, memory backends, state structures, and instrumentation1.

3. **Evaluate:** Run systematic testing (regression suites, golden datasets, task success, and tool accuracy)1.

4. **Deploy:** Roll out safely via staging, canary testing, and feature flags with scoped permissions1.

5. **Monitor & Improve:** Monitor live execution (latency, cost, drift, failure rates) and continuously refine1.

### Question 6.2 (Basic)

What are the three core rules of the MINT Framework (Minimal Intelligence Necessary Tools)?

**Concise Grounded Answer / Grading Guide:**

- **Rule 1: Start Simple:** Build the absolute simplest system that works (e.g., Input $\rightarrow$ Model $\rightarrow$ Output) before adding complex orchestration layers1.

- **Rule 2: Earn Each Layer:** Every added layer (tool use, memory, complex workflows, human-in-the-loop, multi-agent) must justify its overhead in terms of latency, cost, security risk, and maintenance1.

- **Rule 3: Add Complexity Only When Needed:** Climb the MINT ladder only when live testing reveals a clear performance ceiling that simple steps cannot overcome1.

### Question 6.3 (Intermediate)

Why does the MINT framework state that "Most failures aren't model failures. They're complexity you invited in"? Give a practical example of over-engineering.

**Concise Grounded Answer / Grading Guide:**

- **Core Concept:** Developers often rush to build highly autonomous agents with multi-step planners, memory stores, and vector databases when a simpler pattern suffices1. This invites non-deterministic failure modes (looping, tool hallucinations, cost bloat)1.

- **Example of Over-engineering:** Building a full multi-step RAG planner agent to answer questions from a static knowledge base when a simple vector database query inside a single LLM prompt works flawlessly1.

### Question 6.4 (Intermediate)

Explain how to design a "Progress Score" evaluation check to detect whether an agent is making meaningful progress or is stuck in an infinite looping trap.

**Concise Grounded Answer / Grading Guide:**

A Progress Score system evaluates the state after each step1:

- **Good Progress (Continue):** The step output retrieves better context, modifies state with useful/verifiable results, increases confidence, or measurably decreases distance to the goal1.

- **No/Low Progress (Stop/Replan):** The agent repeats the exact same search query, retrieves identical data, leaves confidence unchanged, or has zero movement toward the goal1. If progress is zero across 2 steps, trigger replanning or human escalation1.

### Question 6.5 (Advanced)

Traditional software testing utilizes unit tests with binary assertions. Explain why this approach fails for LLM agents, and how the "Evaluation-Driven Development" (EDDOps) approach unifies offline and online evaluation within a closed loop.

**Concise Grounded Answer / Grading Guide:**

- **Failure of traditional testing:** LLM agents are non-deterministic, pursue under-specified goals, and can achieve success via multiple valid, completely different execution trajectories3031. Binary unit tests cannot handle graded outcomes, semantic correctness, reasoning coherence, or runtime context drift31.

- **EDDOps Closed Loop (Offline + Online):** EDDOps positions evaluation as a continuous governing function32:

- **Offline (Pre-deployment):** Runs batch evaluations on golden datasets, measuring end-to-end pass rates and step-level indicators (plan quality, tool accuracy) to catch regressions before deployment3334.

- **Online (Post-deployment):** Monitors live telemetry, collecting execution traces, user satisfaction, and runtime error anomalies (e.g., drift flags, latency/cost budgets)3334.

- **The closed-loop:** Telemetry failures are clustered, converted into new test cases, and automatically fed back to refine agent prompts, memory policies, and safety cases during redevelopment3536.

## SUB-COMPETENCY 7: agent_interoperability — MCP and A2A

### Question 7.1 (Basic)

What is the Model Context Protocol (MCP)? Describe its three core client-server primitives.

**Concise Grounded Answer / Grading Guide:**

MCP is an open-source standard enabling seamless integration between LLM hosts (like Claude or ChatGPT Desktop) and external tools, databases, and APIs3738. It has three primitives:

- **Tools:** Executable functions with side effects that can change system state and require user consent (e.g., send_email)1439.

- **Resources:** Read-only data sources or files that the host retrieves to provide context, addressed by a unique URI1439.

- **Prompts:** Reusable, user-selectable templates and workflows1439.

### Question 7.2 (Basic)

Compare MCP and A2A (Agent2Agent) protocol. What is the fundamental difference in their communication direction and connection purpose?

**Concise Grounded Answer / Grading Guide:**

- **MCP:** Is a vertical bus14. It connects a single agent (Host) downward to local/remote tools, files, and databases14.

- **A2A:** Is a horizontal bus14. It enables peers (Agent to Agent) built on different vendor stacks and frameworks to discover, communicate, and collaborate with each other1440.

### Question 7.3 (Intermediate)

Explain how MCP solves the "M x N Integration Problem" for AI developers.

**Concise Grounded Answer / Grading Guide:**

- **Before MCP:** If there are 5 different AI clients (Claude, Cursor, ChatGPT, etc.) and 100 tools, developers must build, test, and maintain 500 custom connectors ($M \times N$)14. Tool vendors have to build specific wrappers for every client14.

- **With MCP:** MCP collapses this to $M + N$ integrations (105 connectors)14. A tool vendor builds one standard MCP server, and every MCP-compliant client can instantly discover and invoke its capabilities14. An AI host builds one MCP client, and instantly gains access to the entire ecosystem of MCP servers14.

### Question 7.4 (Intermediate)

Discuss three security attack surfaces introduced by MCP and their corresponding protocol-level or client-level defenses.

**Concise Grounded Answer / Grading Guide:**

Candidates must detail at least three surfaces14:

1. **Tool Poisoning:** Malicious system instructions hidden inside tool descriptions or schemas (e.g., CVE-2025-65138)14. Defense: Vet/pin server versions; run diffs on descriptions14.

2. **Injection via Tool Output:** A compromised tool returns payloads containing malicious system prompts14. Defense: Parse tool IDs and strict verbs; strip systemic patterns before injecting into context14.

3. **Over-scoped Credentials:** Server holds broad OAuth/database access14. Defense: Enforce fine-grained user authentication, short-lived tokens, and rotate credentials14.

4. **Unconfirmed Writes:** Agent initiates destructive commands silently14. Defense: Interpose a mandatory confirmation gate1441.

### Question 7.5 (Advanced)

Under the A2A protocol, agents are "opaque" to one another. Explain how this preserves IP and security, and describe the six elements that constitute a structured A2A "Task Payload" message.

**Concise Grounded Answer / Grading Guide:**

- **Opacity:** A2A allows specialized agents owned by different teams or running on separate servers to collaborate securely without exposing their internal state, proprietary prompts, private database paths, or memory4042. This protects corporate intellectual property and isolates security boundaries42.

Six Elements of A2A Task Payload14:

1. **Task Description:** A plain-language description of the objective (e.g., "Review this employment contract")14.

2. **Message and Inputs:** The actual structured inputs, files, or PDFs needed for the task14.

3. **Constraints:** Deadlines, budget limits, format instructions, and regulatory guardrails the receiver agent must respect14.

4. **State:** The task's lifecycle stage (e.g., submitted, working, completed, failed)14.

5. **Expected Output:** The schema or software artifact shape the receiver is required to return14.

6. **Confidence Signals:** Metadata showing sender certainty or a "should-a-human-see-this" flag14.

copy_allthumb_upthumb_down
