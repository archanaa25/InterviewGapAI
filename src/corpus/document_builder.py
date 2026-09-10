"""
InterviewGap AI - LangChain Document Builder

Converts the validated InterviewGap question corpus from JSONL
records into LangChain Document objects.

The Document contains:

page_content
    Text used by retrieval systems such as BM25 and dense retrieval.

metadata
    Structured attributes used for filtering, identification,
    evaluation, and interview planning.
"""

import json
from pathlib import Path

from langchain_core.documents import Document


def load_jsonl(path):
    """
    Load records from a JSONL file.

    Args:
        path: Path to JSONL file.

    Returns:
        list[dict]: Parsed JSON records.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Corpus file not found: {path}"
        )

    records = []

    with path.open("r", encoding="utf-8") as file:

        for line_number, line in enumerate(
            file,
            start=1,
        ):

            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line "
                    f"{line_number}: {exc}"
                ) from exc

            records.append(record)

    return records


def build_question_document(question):
    """
    Convert one InterviewGap question record into
    a LangChain Document.

    Searchable content contains:
        - question
        - must-have concepts
        - bonus concepts
        - tags

    Metadata contains:
        - question_id
        - role
        - competency
        - sub_competency
        - difficulty
        - question_type
    """

    expected_concepts = question.get(
        "expected_concepts",
        {},
    )

    must_have = expected_concepts.get(
        "must_have",
        [],
    )

    bonus = expected_concepts.get(
        "bonus",
        [],
    )

    tags = question.get(
        "tags",
        [],
    )

    #
    # Text that BM25 / embeddings will search.
    #
    # Concepts enrich matching beyond the question wording. This text is an
    # internal retrieval representation, not the question shown to a candidate.
    search_text = "\n".join(
        [
            f"Question: {question.get('question', '')}",
            "",
            "Must-have concepts:",
            " ".join(must_have),
            "",
            "Bonus concepts:",
            " ".join(bonus),
            "",
            "Tags:",
            " ".join(tags),
        ]
    )

    #
    # Metadata is NOT part of the searchable text.
    # It can later be used for filtering.
    #
    metadata = {
        "question_id": question["question_id"],
        "role": question["role"],
        "competency": question["competency"],
        "sub_competency": question[
            "sub_competency"
        ],
        "difficulty": question["difficulty"],
        "question_type": question[
            "question_type"
        ],
    }

    return Document(
        page_content=search_text,
        metadata=metadata,
    )


def build_question_documents(corpus_path):
    """
    Load the master InterviewGap question corpus
    and convert every record into a LangChain Document.
    """

    questions = load_jsonl(
        corpus_path
    )

    documents = [
        build_question_document(question)
        for question in questions
    ]

    return documents


def main():
    """
    Simple local test for the Document Builder.
    """

    project_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    corpus_path = (
        project_root
        / "data"
        / "prepared"
        / "master"
        / "interview_questions.jsonl"
    )

    print(
        f"Loading corpus: {corpus_path}"
    )

    documents = build_question_documents(
        corpus_path
    )

    print()
    print(
        f"Created {len(documents)} "
        "LangChain Documents"
    )

    if not documents:
        print(
            "No documents found."
        )
        return

    sample = documents[0]

    print()
    print("=" * 70)
    print("SAMPLE DOCUMENT")
    print("=" * 70)

    print()
    print(sample.page_content)

    print()
    print("=" * 70)
    print("METADATA")
    print("=" * 70)

    for key, value in sample.metadata.items():
        print(
            f"{key:<20}: {value}"
        )


if __name__ == "__main__":
    main()