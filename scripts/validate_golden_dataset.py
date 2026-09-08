#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MASTER_QUESTIONS = (
    PROJECT_ROOT
    / "data/prepared/master/interview_questions.jsonl"
)

GOLDEN_FILE = (
    PROJECT_ROOT
    / "data/eval/question_retrieval_golden.jsonl"
)


errors = []
warnings = []


def load_jsonl(path):
    records = []

    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    with path.open("r", encoding="utf-8") as f:

        for line_no, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as exc:
                errors.append(
                    f"{path}:{line_no}: invalid JSON: {exc}"
                )
                continue

            if not isinstance(record, dict):
                errors.append(
                    f"{path}:{line_no}: "
                    "record must be a JSON object"
                )
                continue

            records.append(record)

    return records


def validate_golden_schema(records):

    required_fields = [
        "query_id",
        "query",
        "target_corpus",
        "relevant_question_ids",
        "expected_competency",
        "expected_sub_competency",
        "query_type",
        "difficulty_target",
    ]

    valid_query_types = {
        "semantic",
        "keyword",
        "scenario",
        "cross_concept",
    }

    valid_difficulties = {
        "basic",
        "intermediate",
        "advanced",
    }

    seen_ids = set()

    for record in records:

        qid = record.get(
            "query_id",
            "UNKNOWN_QUERY",
        )

        for field in required_fields:

            if field not in record:
                errors.append(
                    f"{qid}: missing field '{field}'"
                )

        if qid in seen_ids:
            errors.append(
                f"Duplicate query_id: {qid}"
            )

        seen_ids.add(qid)

        if not record.get("query", "").strip():
            errors.append(
                f"{qid}: query cannot be empty"
            )

        relevant = record.get(
            "relevant_question_ids",
            [],
        )

        if not isinstance(relevant, list):
            errors.append(
                f"{qid}: relevant_question_ids "
                "must be a list"
            )

        elif not relevant:
            errors.append(
                f"{qid}: relevant_question_ids "
                "cannot be empty"
            )

        if (
            record.get("query_type")
            not in valid_query_types
        ):
            errors.append(
                f"{qid}: invalid query_type "
                f"'{record.get('query_type')}'"
            )

        if (
            record.get("difficulty_target")
            not in valid_difficulties
        ):
            errors.append(
                f"{qid}: invalid difficulty_target "
                f"'{record.get('difficulty_target')}'"
            )


def validate_targets(golden, master):

    master_by_id = {
        q["question_id"]: q
        for q in master
        if q.get("question_id")
    }

    for record in golden:

        query_id = record.get(
            "query_id",
            "UNKNOWN_QUERY",
        )

        expected_competency = record.get(
            "expected_competency"
        )

        expected_sub = record.get(
            "expected_sub_competency"
        )

        expected_difficulty = record.get(
            "difficulty_target"
        )

        for target_id in record.get(
            "relevant_question_ids",
            []
        ):

            if target_id not in master_by_id:

                errors.append(
                    f"{query_id}: target question "
                    f"'{target_id}' does not exist "
                    "in master corpus"
                )

                continue

            target = master_by_id[target_id]

            actual_competency = target.get(
                "competency"
            )

            actual_sub = target.get(
                "sub_competency"
            )

            actual_difficulty = target.get(
                "difficulty"
            )

            if (
                actual_competency
                != expected_competency
            ):
                errors.append(
                    f"{query_id}: target {target_id} "
                    "competency mismatch: "
                    f"expected '{expected_competency}', "
                    f"found '{actual_competency}'"
                )

            if actual_sub != expected_sub:

                errors.append(
                    f"{query_id}: target {target_id} "
                    "sub_competency mismatch: "
                    f"expected '{expected_sub}', "
                    f"found '{actual_sub}'"
                )

            if (
                actual_difficulty
                != expected_difficulty
            ):
                warnings.append(
                    f"{query_id}: target {target_id} "
                    "difficulty mismatch: "
                    f"expected '{expected_difficulty}', "
                    f"found '{actual_difficulty}'"
                )


def print_summary(golden, master):

    print()
    print("=" * 65)
    print(
        "INTERVIEWGAP AI - GOLDEN DATASET VALIDATION"
    )
    print("=" * 65)

    print()
    print(
        f"Master questions : {len(master)}"
    )

    print(
        f"Golden queries   : {len(golden)}"
    )

    print()
    print("Golden queries by competency")
    print("----------------------------")

    competency_counts = Counter(
        x.get("expected_competency")
        for x in golden
    )

    for name, count in sorted(
        competency_counts.items()
    ):
        print(
            f"{name:<30}: {count}"
        )

    print()
    print("Golden queries by query type")
    print("----------------------------")

    type_counts = Counter(
        x.get("query_type")
        for x in golden
    )

    for name, count in sorted(
        type_counts.items()
    ):
        print(
            f"{name:<20}: {count}"
        )

    print()
    print("Golden queries by difficulty")
    print("----------------------------")

    difficulty_counts = Counter(
        x.get("difficulty_target")
        for x in golden
    )

    for name in [
        "basic",
        "intermediate",
        "advanced",
    ]:
        print(
            f"{name:<15}: "
            f"{difficulty_counts.get(name, 0)}"
        )


def main():

    master = load_jsonl(
        MASTER_QUESTIONS
    )

    golden = load_jsonl(
        GOLDEN_FILE
    )

    validate_golden_schema(
        golden
    )

    validate_targets(
        golden,
        master,
    )

    print_summary(
        golden,
        master,
    )

    if warnings:

        print()
        print("WARNINGS")
        print("--------")

        for warning in warnings:
            print(
                f"WARNING: {warning}"
            )

    if errors:

        print()
        print("VALIDATION FAILED")
        print("-----------------")

        for error in errors:
            print(
                f"ERROR: {error}"
            )

        print()
        print(
            f"{len(errors)} error(s) found."
        )

        sys.exit(1)

    print()
    print("VALIDATION PASSED")
    print()
    print(
        "Golden dataset is ready for "
        "retrieval benchmarking."
    )


if __name__ == "__main__":
    main()
