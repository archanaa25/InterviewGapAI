# InterviewGapAI

AI Engineer interview preparation focused on identifying competency gaps through curated questions and evaluation knowledge.

The repository currently contains the assessment corpus, authoring material, validation script, and an [MVP implementation plan](docs/FIVE_DAY_MVP_IMPLEMENTATION_GUIDE.md). The application runtime is not yet implemented.

## Directory structure

```text
InterviewGapAI/
├── competency_blueprint/   # Competency definitions and assessment expectations
├── config/                 # Reserved for runtime configuration (currently empty)
├── data/
│   ├── raw/notebooklm/     # Source exports and unprocessed question/evaluation material
│   ├── curated/            # Reviewed JSON question banks and evaluation knowledge by competency
│   ├── prepared/           # JSONL exports for downstream ingestion
│   └── eval/               # Reserved for evaluation datasets (currently empty)
├── docs/                   # Architecture, MVP scope, and implementation guidance
├── job_description/        # Canonical AI Engineer role and expectations
├── prompts/                # NotebookLM question-authoring instructions
├── questions/              # Original RAG question material
├── scripts/                # Corpus validation and JSONL export utility
└── README.md
```

Empty directories are workspace placeholders and are not tracked by Git.

`data/curated/` contains `rag`, `agentic_ai`, `llm_fundamentals`, `ai_evaluation`, `ai_system_design`, `ai_security`, and `python_software_engineering`. Each folder pairs `<competency>_questions.json` with `<competency>_evaluation_knowledge.json`; questions link to evaluation records through `evaluation_refs`.

Existing RAG exports are directly under `data/prepared/`; other available exports use competency subdirectories. Python/software engineering exports are not yet present. The validator writes all new exports to `data/prepared/<competency>/`.

## Validate and prepare a corpus

From the repository root, using Python 3 (standard library only):

```bash
python3 scripts/validate_corpus.py rag
```

Replace `rag` with a curated folder name above. The script checks required fields, allowed values, duplicate IDs and question text, and evaluation references. On success, it writes `interview_questions.jsonl` and `evaluation_knowledge.jsonl` to the competency's prepared directory. Structural validation does not establish factual accuracy.

## Keeping this README current

When adding, moving, or removing directories or significant files, update the relevant directory description and usage instructions in the same commit. Document changes that affect setup or data preparation; avoid exhaustive file lists, repeated explanations, and a running change log.
