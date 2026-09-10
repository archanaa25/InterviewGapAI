from collections import Counter
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.validate_evaluation_documents.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation_rag.document_builder import (
    build_evaluation_documents,
)


EXPECTED_COUNT = 35


def main():

    documents = build_evaluation_documents()

    errors = []

    ids = [
        doc.metadata.get("evaluation_id")
        for doc in documents
    ]

    # Number of documents
    if len(documents) != EXPECTED_COUNT:
        errors.append(
            f"Expected {EXPECTED_COUNT} documents, "
            f"found {len(documents)}"
        )

    # Missing IDs
    missing_ids = [
        i
        for i, value in enumerate(ids)
        if not value
    ]

    if missing_ids:
        errors.append(
            f"Documents missing evaluation_id: "
            f"{missing_ids}"
        )

    # Duplicate IDs
    counts = Counter(ids)

    duplicates = [
        evaluation_id
        for evaluation_id, count
        in counts.items()
        if count > 1
    ]

    if duplicates:
        errors.append(
            f"Duplicate evaluation IDs: {duplicates}"
        )

    # Empty content
    empty = [
        doc.metadata.get("evaluation_id")
        for doc in documents
        if not doc.page_content.strip()
    ]

    if empty:
        errors.append(
            f"Documents with empty content: {empty}"
        )

    # Required metadata
    required_metadata = {
        "evaluation_id",
        "competency",
        "sub_competency",
    }

    for doc in documents:

        missing = (
            required_metadata
            - set(doc.metadata)
        )

        if missing:
            errors.append(
                f"{doc.metadata.get('evaluation_id')} "
                f"missing metadata: {sorted(missing)}"
            )

    print("=" * 70)
    print("EVALUATION RAG DOCUMENT VALIDATION")
    print("=" * 70)

    print(f"Documents       : {len(documents)}")
    print(f"Unique IDs      : {len(set(ids))}")
    print(f"Duplicate IDs   : {len(duplicates)}")
    print(f"Empty documents : {len(empty)}")
    print(f"Errors          : {len(errors)}")

    if errors:

        print("\nFAIL")

        for error in errors:
            print(f"  ✗ {error}")

        raise SystemExit(1)

    print("\nStatus: PASS")


if __name__ == "__main__":
    main()
