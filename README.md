# InterviewGapAI

AI Engineer interview preparation focused on identifying competency gaps through curated questions and evaluation knowledge.

The repository contains the assessment corpus, document builder, BM25 retrieval and evaluation, Pinecone ingestion, and an [MVP implementation plan](docs/FIVE_DAY_MVP_IMPLEMENTATION_GUIDE.md). The interview application is not yet implemented.

## Directory structure

```text
InterviewGapAI/
├── competency_blueprint/   # Competency definitions and assessment expectations
├── config/                 # Reserved for runtime configuration (currently empty)
├── data/
│   ├── raw/notebooklm/     # Source exports and unprocessed question/evaluation material
│   ├── curated/            # Reviewed JSON question banks and evaluation knowledge by competency
│   ├── prepared/           # JSONL exports for downstream ingestion
│   │   └── master/        # Combined corpus, manifest, and readable question JSON
│   └── eval/               # Golden retrieval queries, evaluation roadmap, and results
├── docs/                   # Architecture, MVP scope, and implementation guidance
├── job_description/        # Canonical AI Engineer role and expectations
├── prompts/                # NotebookLM question-authoring instructions
├── questions/              # Original RAG question material
├── scripts/                # Corpus validation/build, retrieval evaluation, and Pinecone ingestion
├── src/
│   ├── corpus/             # Converts question records into LangChain documents
│   └── retrieval/          # BM25, Pinecone dense, and hybrid RRF question retrieval
├── .env.example            # Environment variable template; actual keys go in .env
├── .python-version         # Python version used by uv
├── pyproject.toml          # Project metadata and Python dependencies
├── uv.lock                 # Resolved dependency versions for reproducible installation
└── README.md
```

Empty directories are workspace placeholders and are not tracked by Git.

`data/curated/` contains `rag`, `agentic_ai`, `llm_fundamentals`, `ai_evaluation`, `ai_system_design`, `ai_security`, and `python_software_engineering`. Each folder pairs `<competency>_questions.json` with `<competency>_evaluation_knowledge.json`; questions link to evaluation records through `evaluation_refs`.

All seven corpora have exports in `data/prepared/<competency>/`. Legacy RAG exports remain directly under `data/prepared/`; the master builder uses only the seven named competency subdirectories. `data/prepared/master/` contains the combined questions, evaluation knowledge, and `corpus_manifest.json` statistics. Files ending in `_pretty.json` are readable copies of their corresponding JSONL datasets.

`data/prepared/interview_questions.json` and `evaluation_knowledge.json` are readable JSON array copies of the adjacent legacy RAG JSONL files. Refresh these copies when their source files change.

## Python environment and execution

With uv installed, run from the repository root:

```bash
uv sync --locked
```

This creates `.venv` using Python 3.10 and installs the locked dependencies for all current Python modules. Select `.venv/bin/python` as the interpreter in your IDE. Use `uv run python -m <module>` from the repository root so imports from `src` resolve correctly; activation is optional (`source .venv/bin/activate`).

```bash
uv run python -m src.corpus.document_builder
uv run python -m src.retrieval.bm25_retriever
uv run python -m scripts.evaluate_question_retrieval --retriever bm25
```

Use `--retriever dense` or `--retriever hybrid` to evaluate Pinecone search or BM25 + dense retrieval with reciprocal rank fusion. Both require configured OpenAI/Pinecone credentials and an ingested question index. Reports are saved to `data/eval/results/<retriever>_results_v2.json`.

For Pinecone ingestion, create `.env` from `.env.example` if needed, and set `OPENAI_API_KEY` and `PINECONE_API_KEY`. Configure the index name, namespace, cloud, region, and embedding model using the template defaults. The ingestion script currently expects 1536-dimensional embeddings (`text-embedding-3-small`).

```bash
uv run python -m scripts.ingest_pinecone
```

This command makes live OpenAI embedding requests and creates or updates the configured Pinecone index. `.env` and `.venv/` are excluded from Git. Add future dependencies with `uv add <package>` and keep `pyproject.toml` and `uv.lock` together.

## Validate and prepare a corpus

From the repository root:

```bash
uv run python -m scripts.validate_corpus rag
```

Replace `rag` with a curated folder name above. The script checks required fields, allowed values, duplicate IDs and question text, and evaluation references. On success, it writes `interview_questions.jsonl` and `evaluation_knowledge.jsonl` to the competency's prepared directory. Structural validation does not establish factual accuracy.

To rebuild all prepared corpora, combine them, and validate the golden retrieval dataset:

```bash
for corpus in rag agentic_ai llm_fundamentals ai_evaluation python_software_engineering ai_system_design ai_security; do
    uv run python -m scripts.validate_corpus "$corpus" || exit 1
done
uv run python -m scripts.build_corpus && uv run python -m scripts.validate_golden_dataset
```

The master builder checks global IDs and evaluation references. The golden validator checks query fields and target questions against the master corpus; it does not measure retrieval performance. These scripts do not regenerate the `_pretty.json` copies; keep them synchronized when their JSONL sources change.

## Keeping this README current

When adding, moving, or removing directories or significant files, update the relevant directory description and usage instructions in the same commit. Document changes that affect setup or data preparation; avoid exhaustive file lists, repeated explanations, and a running change log.
