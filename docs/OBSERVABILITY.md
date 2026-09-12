# Shared production telemetry

`src.observability` provides JSON events, request correlation, nested timed spans,
metadata sanitization, and optional LangSmith export. Importing the module does
not configure handlers or enable export. Application startup owns configuration.

## Application integration

For an interactive resume upload, open
[`notebooks/02_resume_langsmith.ipynb`](../notebooks/02_resume_langsmith.ipynb).
Run setup, upload a TXT/Markdown/text-based PDF, run analysis, and use the final
dashboard link cell. Setup explicitly enables LangSmith for that notebook after
checking `LANGSMITH_API_KEY` and `OPENAI_API_KEY`; it does not change `.env`.
The upload widget requires `uv sync --locked --group dev` and the project kernel.
Resume processing uses live OpenAI calls; rerun only the link lookup cell to
refresh the dashboard link without repeating those calls. Set
`INCLUDE_INTERVIEW=True` to also run planning and question selection with Pinecone.

The run named `intake.resume` contains `resume.extract` and `resume.analyze`
children, plus optional `interview.plan` and `interview.select_questions` spans.
Only sanitized operational metadata is exported. Models are available locally
in the notebook, and uploaded bytes are not saved as a repository file.

Install locked dependencies with `uv sync --locked`. Load environment settings
before configuring telemetry, then configure once in each worker process:

```python
from dotenv import load_dotenv
from src.observability import (
    configure_observability, request_context, trace_span, log_event,
    flush_telemetry,
)
from src.evaluation_rag.service import retrieve_evaluation_context

load_dotenv()  # The application can supply its explicit .env path here.
configure_observability()  # JSON to stdout; export follows LANGSMITH_TRACING.

# At an API/worker boundary, use opaque IDs from your application records.
with request_context(
    request_id="request-123",
    interview_id="interview-456",
    question_id="RAG-001",
) as correlation:
    with trace_span("evaluate_answer", prompt_version="v1", rubric_version="v1"):
        context = retrieve_evaluation_context(
            question="How does chunk size affect retrieval?",
            candidate_answer="Smaller chunks are always better.",
            competency="rag",
        )
        log_event("assessment.evidence_ready", result_count=len(context["retrieved_knowledge"]))
    # Attach correlation['request_id'] and correlation['trace_id'] to the saved
    # assessment or response so support staff can locate the corresponding trace.

# In the application's shutdown hook (not after each HTTP request):
flush_telemetry(timeout=2.0)
```

Each operation gets a fresh UUID `trace_id` and generated `request_id` unless
one is supplied. Reuse `interview_id` across preparation, answer submission,
and final-report operations. Reuse `question_id` for a question within that
interview. Correlation IDs must be opaque, 1–128 characters, using letters,
digits, underscores, or hyphens; never use candidate names or emails.

Nested spans share correlation IDs and have distinct `span_id` values and a
`parent_span_id`. Context is restored even after errors. `ContextVar` isolates
concurrent asyncio tasks. A new request context also detaches it from any
parent span. Pass the correlation IDs explicitly in queue messages or across
processes; this module does not implement distributed trace-header propagation.
Manually created threads need explicit context propagation too.

`@traced("operation.name")` supports ordinary synchronous functions and
coroutines. It deliberately does not inspect arguments or return values. For
generators/streaming responses, wrap the actual consumption in `trace_span`.
Add explicitly chosen metadata using `span.set_attributes(...)` or `log_event`.

## Events and instrumentation

Every JSON line includes timestamp, level, event, current correlation IDs,
span ID, and a sanitized `attributes` object. Span start/end events add operation,
parent span, duration in milliseconds, status, and exception type on failure.
Exceptions retain their original type and instance for the application caller.

Currently instrumented:

```text
evaluation_rag.request                 includes lazy service initialization
└── evaluation_rag.retrieve_context
    └── evaluation_rag.retrieve
        ├── evaluation_rag.dense_search
        │   ├── evaluation_rag.embed_query       model, tokens
        │   └── evaluation_rag.pinecone_search  namespace, filters, k, count
        └── evaluation_rag.results              evidence IDs, ranks, scores
```

Calling an instrumented method without a request context creates one
automatically. Supply your own context at the application boundary to associate
it with an interview and question. Resume extraction, analysis, planning, and the
question-selection entry point also have spans. The Evaluation Agent can use the
same helpers when integrated. Functions return their original application outputs.

The dedicated `interviewgap.telemetry` logger does not propagate to root logging
or modify third-party handlers. Reconfiguration replaces its own handler to
avoid duplicate events. Existing print statements and third-party logs are not
automatically converted or sanitized. Use `log_event` for application telemetry.
Configure your deployment's stdout collector for persistence and retention;
this module does not create a log database or rotate files.

## Sanitization

Automatic function input/output capture is disabled. Question/answer text,
resume contents, prompts, messages, retrieved text, credentials, and identifying
fields are redacted when passed under recognized metadata keys. Common email,
phone, bearer-token, and API-token patterns are redacted from strings. Exception
messages and tracebacks are not emitted. Lists, depth, and string length are
bounded; unknown objects are omitted without calling their `repr` or `str`.
Sanitization copies values and never modifies business inputs or outputs.

Only submit operational metadata. Pattern matching is not a comprehensive PII
detector: names, addresses, novel credentials, or raw user text under arbitrary
keys can evade it. Do not put those values in event names, IDs, or attributes.
Use versioned evidence IDs to locate content in the application store. Logging
failure messages by type avoids accidental provider-response and payload leaks.

## Optional LangSmith export

Local JSON logging works with:

```dotenv
LANGSMITH_TRACING=false
LANGSMITH_PROJECT=interviewgap-ai
```

To export, set `LANGSMITH_TRACING=true` and configure `LANGSMITH_API_KEY` in the
environment, then call `configure_observability()` at startup. For a forced
offline run use `configure_observability(tracing_enabled=False)`.

The exporter sends explicitly sanitized metadata through LangSmith `RunTree`,
with empty inputs and metadata-only outputs. Root run IDs match local trace IDs,
and nested runs match local spans. It does not wrap LLM clients or capture raw
messages. Embedding token counts are metadata; automatic LLM cost dashboards
and online judges are outside this implementation.

Export and logging exceptions do not replace application results or errors.
Export failures emit `telemetry.export_failed` locally with the exception type.
Use the bounded `flush_telemetry` hook at shutdown for best-effort delivery;
telemetry is not a durable audit ledger and events can be lost during failures.

Implementation references:
[LangSmith manual instrumentation](https://docs.langchain.com/langsmith/annotate-code)
and [sensitive-data masking](https://docs.langchain.com/langsmith/mask-inputs-outputs).

## Verification

Offline tests exercise redaction, real SDK run-tree construction with blocked
exports, nested IDs, concurrent tasks, error propagation, broken log sinks,
export failures, and service integration:

```bash
uv run --locked pytest
```

Use pytest rather than `python -m unittest discover -s tests`. Discovery
only collects `unittest.TestCase` subclasses, so it silently skips any
pytest-style file — `tests/test_evaluation_agent.py` ran nowhere under that
command. pytest executes `unittest.TestCase` classes natively and
`pyproject.toml` points it at both `tests/` and `ui/tests/`, so one command
covers every test in either style. To run one file:

```bash
uv run --locked pytest tests/test_observability.py
```

The existing live smoke script enables JSON telemetry on stderr while keeping
its human-readable output on stdout:

```bash
uv run python scripts/test_evaluation_rag_service.py
```

That smoke script uses live embedding/vector services. Offline tests do not.
