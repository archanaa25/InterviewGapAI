"""
Document builder for the InterviewGapAI Evaluation RAG corpus.

Converts evaluation_knowledge.jsonl records into LangChain Documents.

The resulting documents are used by Evaluation RAG retrieval.
"""

import json
from pathlib import Path
from typing import List

from langchain_core.documents import Document


DEFAULT_CORPUS_PATH = Path(
    "data/prepared/master/evaluation_knowledge.jsonl"
)


def load_evaluation_records(
    path: Path = DEFAULT_CORPUS_PATH,
) -> List[dict]:
    """Load evaluation knowledge records from JSONL."""

    if not path.exists():
        raise FileNotFoundError(
            f"Evaluation corpus not found: {path}"
        )

    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line {line_number} "
                    f"in {path}: {exc}"
                ) from exc

            records.append(record)

    return records


def build_page_content(record: dict) -> str:
    """
    Build the text that will be indexed for retrieval.

    Include the knowledge-bearing fields that should influence
    semantic and lexical retrieval.
    """

    parts = []

    topic = record.get("topic")
    if topic:
        parts.append(f"Topic: {topic}")

    content = record.get("content")
    if content:
        parts.append(f"Content:\n{content}")

    key_concepts = record.get("key_concepts", []) or []

    if key_concepts:
        concepts_text = "\n".join(
            f"- {concept}"
            for concept in key_concepts
        )

        parts.append(
            f"Key Concepts:\n{concepts_text}"
        )

    misconceptions = (
        record.get("common_misconceptions", [])
        or []
    )

    if misconceptions:
        misconceptions_text = "\n".join(
            f"- {item}"
            for item in misconceptions
        )

        parts.append(
            f"Common Misconceptions:\n"
            f"{misconceptions_text}"
        )

    return "\n\n".join(parts)


def build_metadata(record: dict) -> dict:
    """
    Build retrieval metadata.

    Metadata is kept separate from page_content so it can later
    support filtering and evaluation.
    """

    metadata = {
        "evaluation_id": record["evaluation_id"],
        "role": record.get("role"),
        "competency": record.get("competency"),
        "sub_competency": record.get(
            "sub_competency"
        ),
    }

    # Pinecone metadata supports simple scalar/list values.
    tags = record.get("tags", []) or []

    if tags:
        metadata["tags"] = tags

    source = record.get("source", {}) or {}

    if source:
        metadata["source_type"] = source.get(
            "source_type"
        )

        metadata["source_document"] = source.get(
            "document"
        )

        metadata["source_section"] = source.get(
            "section"
        )

    # Remove None values.
    return {
        key: value
        for key, value in metadata.items()
        if value is not None
    }


def build_document(record: dict) -> Document:
    """Convert one evaluation record into a LangChain Document."""

    if "evaluation_id" not in record:
        raise ValueError(
            "Evaluation record is missing evaluation_id"
        )

    page_content = build_page_content(record)

    if not page_content.strip():
        raise ValueError(
            f"Evaluation record "
            f"{record['evaluation_id']} "
            f"has no indexable content."
        )

    return Document(
        page_content=page_content,
        metadata=build_metadata(record),
    )


def build_evaluation_documents(
    path: Path = DEFAULT_CORPUS_PATH,
) -> List[Document]:
    """
    Load the evaluation corpus and convert all records into
    LangChain Documents.
    """

    records = load_evaluation_records(path)

    documents = [
        build_document(record)
        for record in records
    ]

    return documents


def main():

    documents = build_evaluation_documents()

    print(
        f"Created {len(documents)} "
        f"Evaluation RAG documents"
    )

    if not documents:
        return

    print("\n" + "=" * 80)
    print("SAMPLE DOCUMENT")
    print("=" * 80)

    document = documents[0]

    print("\nPAGE CONTENT\n")
    print(document.page_content)

    print("\nMETADATA\n")

    print(
        json.dumps(
            document.metadata,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()