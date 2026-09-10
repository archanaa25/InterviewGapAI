import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.evaluate_concept_coverage.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.coverage_judge import judge_concept_coverage


QUESTIONS_FILE = PROJECT_ROOT / (
    "data/prepared/master/interview_questions.jsonl"
)

EVALUATION_FILE = PROJECT_ROOT / (
    "data/prepared/master/evaluation_knowledge.jsonl"
)

OUTPUT_FILE = PROJECT_ROOT / (
    "data/eval/evaluation_concept_coverage.jsonl"
)


def load_jsonl(path):
    records = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(json.loads(line))

    return records


def build_evaluation_text(records):
    parts = []

    for record in records:

        parts.append(
            f"Topic: {record.get('topic', '')}"
        )

        parts.append(
            f"Content: {record.get('content', '')}"
        )

        key_concepts = record.get(
            "key_concepts",
            [],
        ) or []

        if key_concepts:
            parts.append(
                "Key concepts:\n- "
                + "\n- ".join(key_concepts)
            )

        misconceptions = record.get(
            "common_misconceptions",
            [],
        ) or []

        if misconceptions:
            parts.append(
                "Common misconceptions:\n- "
                + "\n- ".join(misconceptions)
            )

    return "\n\n".join(parts)


def main():

    questions = load_jsonl(QUESTIONS_FILE)
    evaluations = load_jsonl(EVALUATION_FILE)

    eval_by_id = {
        item["evaluation_id"]: item
        for item in evaluations
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = []

    total_concepts = sum(
        len(
            (
                q.get("expected_concepts", {})
                or {}
            ).get("must_have", [])
            or []
        )
        for q in questions
    )

    print(
        f"Questions          : {len(questions)}"
    )

    print(
        f"Must-have concepts : {total_concepts}\n"
    )

    processed = 0

    for question in questions:

        question_id = question["question_id"]

        refs = (
            question.get("evaluation_refs", [])
            or []
        )

        referenced_records = [
            eval_by_id[ref]
            for ref in refs
            if ref in eval_by_id
        ]

        evaluation_text = build_evaluation_text(
            referenced_records
        )

        expected = (
            question.get("expected_concepts", {})
            or {}
        )

        must_have = (
            expected.get("must_have", [])
            or []
        )

        for concept in must_have:

            processed += 1

            print(
                f"[{processed}/{total_concepts}] "
                f"{question_id}"
            )

            result = judge_concept_coverage(
                question_id=question_id,
                question=question["question"],
                concept=concept,
                evaluation_knowledge=evaluation_text,
            )

            record = result.model_dump()

            # Make enum JSON-friendly.
            record["coverage"] = (
                result.coverage.value
            )

            record["competency"] = (
                question["competency"]
            )

            record["sub_competency"] = (
                question["sub_competency"]
            )

            record["evaluation_refs"] = refs

            results.append(record)

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in results:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    counts = Counter(
        result["coverage"]
        for result in results
    )

    print("\n" + "=" * 70)
    print("SEMANTIC CONCEPT COVERAGE")
    print("=" * 70)

    for label in [
        "COVERED",
        "PARTIAL",
        "NOT_COVERED",
    ]:

        count = counts[label]

        pct = (
            count / len(results) * 100
            if results
            else 0
        )

        print(
            f"{label:<15}: "
            f"{count:>3} "
            f"({pct:.2f}%)"
        )

    print(
        f"\nSaved: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
