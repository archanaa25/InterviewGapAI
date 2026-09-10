import json
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


QUESTIONS_FILE = PROJECT_ROOT / (
    "data/prepared/master/interview_questions.jsonl"
)

EVALUATION_FILE = PROJECT_ROOT / (
    "data/prepared/master/evaluation_knowledge.jsonl"
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
    evaluations = load_jsonl(EVALUATION_FILE)

    print("=" * 90)
    print("EVALUATION CORPUS COVERAGE ANALYSIS")
    print("=" * 90)

    print(f"\nInterview questions : {len(questions)}")
    print(f"Evaluation records  : {len(evaluations)}")

    # Explicit references allow evaluation records to support related topics.
    eval_lookup = {record["evaluation_id"]: record for record in evaluations}

    covered = []
    uncovered = []

    competency_stats = defaultdict(
        lambda: {
            "total": 0,
            "covered": 0,
        }
    )

    # --------------------------------------------------
    # Check every interview question
    # --------------------------------------------------

    for question in questions:

        competency = question["competency"]
        sub_competency = question["sub_competency"]

        competency_stats[competency]["total"] += 1

        # Coverage means every explicit reference resolves. A matching topic
        # label alone is insufficient, and one valid link cannot hide a broken one.
        refs = question.get("evaluation_refs", [])
        missing_refs = [ref for ref in refs if ref not in eval_lookup]
        matches = [eval_lookup[ref] for ref in dict.fromkeys(refs) if ref in eval_lookup]

        if refs and not missing_refs:

            competency_stats[competency]["covered"] += 1

            covered.append(
                {
                    "question_id": question["question_id"],
                    "competency": competency,
                    "sub_competency": sub_competency,
                    "evaluation_ids": [
                        r["evaluation_id"]
                        for r in matches
                    ],
                }
            )

        else:

            uncovered.append(
                {
                    "question_id": question["question_id"],
                    "competency": competency,
                    "sub_competency": sub_competency,
                    "question": question.get(
                        "question",
                        "",
                    ),
                    "must_have_concepts": question.get(
                        "expected_concepts", {}
                    ).get("must_have", []),
                    "reference_issue": (
                        f"Unknown evaluation IDs: {missing_refs}"
                        if missing_refs else "No evaluation_refs supplied"
                    ),
                }
            )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    total = len(questions)

    covered_count = len(covered)

    coverage_pct = (
        covered_count / total * 100
        if total
        else 0
    )

    print("\n" + "-" * 90)

    print("OVERALL COVERAGE (explicit evaluation_refs)")

    print("-" * 90)

    print(f"Covered   : {covered_count}")
    print(f"Uncovered : {len(uncovered)}")
    print(f"Coverage  : {coverage_pct:.2f}%")

    # --------------------------------------------------
    # Competency coverage
    # --------------------------------------------------

    print("\n" + "-" * 90)

    print("COVERAGE BY COMPETENCY")

    print("-" * 90)

    for competency, stats in sorted(
        competency_stats.items()
    ):

        total_comp = stats["total"]
        covered_comp = stats["covered"]

        pct = (
            covered_comp / total_comp * 100
            if total_comp
            else 0
        )

        print(
            f"{competency:<35}"
            f"{covered_comp:>3}/{total_comp:<3}"
            f" {pct:>6.2f}%"
        )

    # --------------------------------------------------
    # Evaluation record utilization
    # --------------------------------------------------

    # Count links from fully covered questions. This is reference utilization,
    # not proof that the evaluation content is sufficient for accurate scoring.
    usage = Counter()

    for item in covered:
        for evaluation_id in item["evaluation_ids"]:
            usage[evaluation_id] += 1

    print("\n" + "-" * 90)

    print("EVALUATION RECORD UTILIZATION")

    print("-" * 90)

    for record in evaluations:

        evaluation_id = record["evaluation_id"]

        print(
            f"{evaluation_id:<35}"
            f"{usage[evaluation_id]:>3} questions"
        )

    # --------------------------------------------------
    # Uncovered questions
    # --------------------------------------------------

    if uncovered:

        print("\n" + "-" * 90)

        print("UNCOVERED QUESTIONS")

        print("-" * 90)

        for item in uncovered:

            print(
                f"\n{item['question_id']}"
            )

            print(
                f"  Competency     : "
                f"{item['competency']}"
            )

            print(
                f"  Sub-competency : "
                f"{item['sub_competency']}"
            )

            print(
                f"  Question       : "
                f"{item['question']}"
            )

            print(
                f"  Must-have      : "
                f"{item['must_have_concepts']}"
            )
            print(f"  Reference issue: {item['reference_issue']}")

    # --------------------------------------------------
    # Evaluation records never mapped
    # --------------------------------------------------

    unused = [
        record["evaluation_id"]
        for record in evaluations
        if usage[record["evaluation_id"]] == 0
    ]

    print("\n" + "-" * 90)

    print("UNUSED EVALUATION RECORDS")

    print("-" * 90)

    if unused:

        for evaluation_id in unused:
            print(evaluation_id)

    else:
        print("None")

    print("\n" + "=" * 90)


if __name__ == "__main__":
    main()
