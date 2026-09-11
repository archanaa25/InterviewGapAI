1. What kinds of task characteristics justify using an autonomous agent instead of a simpler deterministic workflow?

ReAct Loop - Reason , Act and Observe

2. Using a simple analogy, what roles do Query, Key, and Value play in self-attention?

Query - What am i looking for? Key - What do i offer? Value - Actual content

3. Under what conditions or operational constraints are deterministic workflows preferred over agentic workflows? Give three concrete scenarios.

FInancial Transaction involving System

4. How do CBOW and Skip-gram differ in what they learn to predict?

CBOW (Continuous Bag of Words) — predicts the target from context Skip-gram — predicts the context from the target

5. How would you build an evaluation dataset to test whether a RAG assistant correctly abstains when supporting evidence is missing?

Build a golden dataset and run all queries with the retrieval

6. A multi-tenant RAG assistant is told in its system prompt to only answer using the current customer's documents. Why is that not sufficient access control?

Context or retrieval knowledge may not be correct

7. Describe a production RAG architecture with separate ingestion and query pipelines. How would you handle document updates, access control, retrieval, reranking, generation, and observability?

Document updates via ingestion , Retrieval can be bm25 or dense or hybrid based on the eval. Reranking has to be done on chunks and then it has to be sent for generation to LLM . Eval has to be done on production system to have observability

8. How would you calibrate an LLM-as-a-judge against human expert evaluations before trusting it for production decisions?

Build a human dataset - golden dataset

9. How would you structure a Python service containing ingestion, retrieval, LLM calls, evaluation, and API endpoints so that individual components can evolve independently?

Skipped

10. Design a production AI assistant that uses enterprise knowledge and external tools. What boundaries would you create between retrieval, reasoning, tool execution, guardrails, and observability?

This is fundamentally a separation-of-concerns problem under trust asymmetry — retrieval and tools touch untrusted/sensitive data, reasoning is probabilistic and non-deterministic, and guardrails/observability need to sit outside the trust boundary of the LLM itself so they can't be silently bypassed by a clever prompt