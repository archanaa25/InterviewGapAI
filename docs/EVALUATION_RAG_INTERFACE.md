# Evaluation RAG interface

The MVP uses dense retrieval with an exact competency filter and top-k 5.
Defaults: OpenAI `text-embedding-3-small`, Pinecone index `interviewgap-ai`,
namespace `evaluation-v1`. No retrieval tuning is included in this handoff.

## Calling from the Evaluation Agent

The service wrapper offers a reusable client and an agent-ready context envelope:

```python
from src.evaluation_rag.service import retrieve_evaluation_context

context = retrieve_evaluation_context(
    question="How does chunk size affect retrieval quality?",
    candidate_answer="Smaller chunks are always better.",
    competency="rag",
)
evidence = context["retrieved_knowledge"]
```

The response contains `question`, `competency`, and `retrieved_knowledge`.
Each evidence entry has `evaluation_id`, `rank`, `score`, and `content`.
Retrieval uses only the question; the answer is reserved for downstream
assessment. The lower-level retriever is also available as shown below.

Run `uv sync --locked` in this repository. Configure `OPENAI_API_KEY` and
`PINECONE_API_KEY` in the root `.env`. The evaluation corpus must already be
ingested into the configured index and namespace. Instantiate once and reuse:

```python
from src.evaluation_rag.dense_retriever import EvaluationDenseRetriever

retriever = EvaluationDenseRetriever()

evidence = retriever.retrieve(
    query="How does chunk size affect retrieval quality?",
    competency="rag",
)

context = "\n\n".join(
    f"[{item['evaluation_id']}]\n{item['search_text']}"
    for item in evidence
)
```

Use the interview question text as `query` and the question's `competency`
field as the filter. The competency must match the corpus slug exactly, for
example `rag` or `agentic_ai`. The agent supplies the candidate's answer
separately when assessing it against the retrieved evidence.

`retrieve(query: str, competency: str, k: int = 5)` returns a list of typed,
JSON-serializable dictionaries in descending similarity order:

| Field | Meaning |
| --- | --- |
| `evaluation_id` | Evidence ID to retain for citations and traceability |
| `rank` | One-based result rank |
| `score` | Vector similarity score; not an answer grade or confidence probability |
| `competency` | Corpus competency, or `None` when metadata is absent |
| `sub_competency` | Corpus sub-competency, or `None` |
| `topic` | Optional topic; may be `None` with the current ingestion format |
| `search_text` | Evidence text stored during ingestion; empty if missing |

The result can contain fewer than k records, including an empty list. There
is no fallback to unfiltered retrieval. The agent should handle unavailable
or empty evidence explicitly before generating an assessment. Blank query or
competency and nonpositive/noninteger k raise `ValueError`. Missing API keys
raise `RuntimeError` at initialization; embedding and vector service errors
propagate so the application can apply its own retry/error handling.

The existing `search(query, k=None, filters=None)` interface remains available
for baseline experiments. Agent integrations should use `retrieve()` to keep
the competency filter mandatory. Its default k is always 5, independent of
the legacy constructor's search default.

The index, namespace, and model can be overridden using `PINECONE_INDEX_NAME`,
`PINECONE_EVALUATION_NAMESPACE`, and `OPENAI_EMBEDDING_MODEL`. Keep ingestion
and retrieval settings aligned. An empty evaluation namespace uses
`evaluation-v1`.

## Validation

Reported MVP baseline for 112 golden queries: Recall@1 0.9375, Recall@3 0.9911,
Recall@5 1.0000, MRR 0.9650, NDCG@5 0.9740. These are golden-set measurements,
not a guarantee for unseen questions.

The competency benchmark now calls the same `retrieve()` entry point:

```bash
uv run python scripts/evaluate_evaluation_rag_dense_competency.py
```

This uses live OpenAI and Pinecone services and writes
`data/eval/evaluation_rag_dense_competency_results.jsonl`.
Run the offline interface checks without service calls:

```bash
uv run python -m unittest discover -s tests -p 'test_evaluation_dense_retriever.py'
```
