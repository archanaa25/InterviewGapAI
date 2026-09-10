import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.validate_evaluation_rag_golden.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation_rag.document_builder import (
    build_evaluation_documents,
)


GOLDEN_FILE = Path(
    "data/eval/evaluation_rag_golden.jsonl"
)

EXPECTED_QUERIES = 112


def load_jsonl(path):
    records = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records


def main():

    golden = load_jsonl(GOLDEN_FILE)

    documents = build_evaluation_documents()

    document_ids = {
        doc.metadata["evaluation_id"]
        for doc in documents
    }

    errors = []

    # -----------------------------------
    # Record count
    # -----------------------------------

    if len(golden) != EXPECTED_QUERIES:

        errors.append(
            f"Expected {EXPECTED_QUERIES} queries, "
            f"found {len(golden)}"
        )

    # -----------------------------------
    # Duplicate query IDs
    # -----------------------------------

    query_ids = [
        item["query_id"]
        for item in golden
    ]

    if len(query_ids) != len(set(query_ids)):

        errors.append(
            "Duplicate query IDs found."
        )

    # -----------------------------------
    # Validate each record
    # -----------------------------------

    for item in golden:

        query_id = item.get("query_id")

        if not item.get("query", "").strip():

            errors.append(
                f"{query_id}: empty query"
            )

        relevant_ids = (
            item.get("relevant_ids", [])
            or []
        )

        if not relevant_ids:

            errors.append(
                f"{query_id}: no relevant IDs"
            )

            continue

        unknown_ids = (
            set(relevant_ids)
            - document_ids
        )

        if unknown_ids:

            errors.append(
                f"{query_id}: unknown evaluation IDs "
                f"{sorted(unknown_ids)}"
            )

    print("=" * 70)
    print("EVALUATION RAG GOLDEN VALIDATION")
    print("=" * 70)

    print(f"Golden queries      : {len(golden)}")
    print(f"Evaluation documents: {len(documents)}")
    print(f"Unique query IDs    : {len(set(query_ids))}")
    print(f"Errors              : {len(errors)}")

    if errors:

        print("\nFAIL\n")

        for error in errors:
            print(f"  ✗ {error}")

        raise SystemExit(1)

    print("\nStatus: PASS")


if __name__ == "__main__":
    main()
