"""
Create the golden retrieval dataset for Evaluation RAG.

Each interview question becomes a retrieval query.

The question's evaluation_refs are treated as the relevant
evaluation knowledge document IDs.
"""

import json
from pathlib import Path


QUESTIONS_FILE = Path(
    "data/prepared/master/interview_questions.jsonl"
)

OUTPUT_FILE = Path(
    "data/eval/evaluation_rag_golden.jsonl"
)


def load_jsonl(path):
    records = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records


def main():

    questions = load_jsonl(QUESTIONS_FILE)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    golden_records = []

    for question in questions:

        evaluation_refs = (
            question.get("evaluation_refs", [])
            or []
        )

        if not evaluation_refs:
            raise ValueError(
                f"{question['question_id']} "
                f"has no evaluation_refs"
            )

        record = {
            "query_id": question["question_id"],
            "query": question["question"],
            "relevant_ids": evaluation_refs,
            "competency": question["competency"],
            "sub_competency": question[
                "sub_competency"
            ],
            "difficulty": question["difficulty"],
        }

        golden_records.append(record)

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in golden_records:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print("=" * 70)
    print("EVALUATION RAG GOLDEN DATASET")
    print("=" * 70)

    print(f"Questions       : {len(questions)}")
    print(f"Golden queries  : {len(golden_records)}")
    print(f"Output          : {OUTPUT_FILE}")

    print("\nSample:\n")

    print(
        json.dumps(
            golden_records[0],
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()