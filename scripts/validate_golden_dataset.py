#!/usr/bin/env python3

import json
import sys
from collections import Counter
from pathlib import Path


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


VALID_QUERY_TYPES = {
    "semantic",
    "keyword",
    "scenario",
    "cross_concept",
    "hard_semantic",
    "ambiguous",
    "near_neighbor",
    "negative",
}

VALID_DIFFICULTIES = {
    "basic",
    "intermediate",
    "advanced",
}

VALID_BEHAVIORS = {
    "retrieve",
    "retrieve_any_relevant",
    "no_relevant_question",
}


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
                    f"{path}:{line_no}: "
                    f"invalid JSON: {exc}"
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


def validate_schema(records):

    required_fields = [
        "query_id",
        "query",
        "target_corpus",
        "relevant_question_ids",
        "query_type",
        "expected_behavior",
    ]

    seen_ids = set()

    for record in records:

        query_id = record.get(
            "query_id",
            "UNKNOWN_QUERY",
        )

        for field in required_fields:

            if field not in record:

                errors.append(
                    f"{query_id}: "
                    f"missing field '{field}'"
                )

        if query_id in seen_ids:

            errors.append(
                f"Duplicate query_id: {query_id}"
            )

        seen_ids.add(query_id)

        if not record.get("query", "").strip():

            errors.append(
                f"{query_id}: query cannot be empty"
            )

        query_type = record.get("query_type")

        if query_type not in VALID_QUERY_TYPES:

            errors.append(
                f"{query_id}: invalid query_type "
                f"'{query_type}'"
            )

        behavior = record.get(
            "expected_behavior"
        )

        if behavior not in VALID_BEHAVIORS:

            errors.append(
                f"{query_id}: invalid "
                f"expected_behavior '{behavior}'"
            )

        relevant_ids = record.get(
            "relevant_question_ids"
        )

        if not isinstance(relevant_ids, list):

            errors.append(
                f"{query_id}: "
                "relevant_question_ids "
                "must be a list"
            )

            continue

        #
        # Positive / ambiguous cases need
        # at least one acceptable target.
        #
        if behavior in {
            "retrieve",
            "retrieve_any_relevant",
        }:

            if not relevant_ids:

                errors.append(
                    f"{query_id}: "
                    f"{behavior} requires at least "
                    "one relevant_question_id"
                )

        #
        # Negative cases MUST have no target.
        #
        if behavior == "no_relevant_question":

            if relevant_ids:

                errors.append(
                    f"{query_id}: negative query "
                    "must have empty "
                    "relevant_question_ids"
                )

        #
        # Difficulty may be null for ambiguous
        # and negative queries.
        #
        difficulty = record.get(
            "difficulty_target"
        )

        if (
            difficulty is not None
            and difficulty
            not in VALID_DIFFICULTIES
        ):

            errors.append(
                f"{query_id}: invalid "
                f"difficulty_target "
                f"'{difficulty}'"
            )


def validate_targets(
    golden,
    master,
):

    master_by_id = {
        q["question_id"]: q
        for q in master
        if q.get("question_id")
    }

    for record in golden:

        query_id = record["query_id"]

        behavior = record[
            "expected_behavior"
        ]

        #
        # Negative queries intentionally
        # have no target.
        #
        if behavior == "no_relevant_question":
            continue

        expected_competency = record.get(
            "expected_competency"
        )

        expected_sub = record.get(
            "expected_sub_competency"
        )

        expected_difficulty = record.get(
            "difficulty_target"
        )

        for target_id in record[
            "relevant_question_ids"
        ]:

            if target_id not in master_by_id:

                errors.append(
                    f"{query_id}: target "
                    f"'{target_id}' does not exist"
                )

                continue

            target = master_by_id[target_id]

            #
            # Only check metadata when the
            # golden record specifies it.
            #
            if expected_competency is not None:

                actual = target.get(
                    "competency"
                )

                if actual != expected_competency:

                    errors.append(
                        f"{query_id}: {target_id} "
                        "competency mismatch: "
                        f"expected "
                        f"'{expected_competency}', "
                        f"found '{actual}'"
                    )

            if expected_sub is not None:

                actual = target.get(
                    "sub_competency"
                )

                if actual != expected_sub:

                    errors.append(
                        f"{query_id}: {target_id} "
                        "sub_competency mismatch: "
                        f"expected '{expected_sub}', "
                        f"found '{actual}'"
                    )

            #
            # Difficulty is intentionally
            # optional for ambiguous queries.
            #
            if expected_difficulty is not None:

                actual = target.get(
                    "difficulty"
                )

                if actual != expected_difficulty:

                    warnings.append(
                        f"{query_id}: {target_id} "
                        "difficulty mismatch: "
                        f"expected "
                        f"'{expected_difficulty}', "
                        f"found '{actual}'"
                    )


def print_summary(
    golden,
    master,
):

    print()
    print("=" * 70)
    print(
        "INTERVIEWGAP AI - "
        "GOLDEN DATASET V2 VALIDATION"
    )
    print("=" * 70)

    print()
    print(
        f"Master questions : {len(master)}"
    )

    print(
        f"Golden queries   : {len(golden)}"
    )

    print()
    print("Expected behavior")
    print("-----------------")

    behavior_counts = Counter(
        x.get("expected_behavior")
        for x in golden
    )

    for name, count in sorted(
        behavior_counts.items()
    ):

        print(
            f"{name:<25}: {count}"
        )

    print()
    print("Query types")
    print("-----------")

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


def main():

    master = load_jsonl(
        MASTER_QUESTIONS
    )

    golden = load_jsonl(
        GOLDEN_FILE
    )

    validate_schema(
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

        sys.exit(1)

    print()
    print("VALIDATION PASSED")
    print()
    print(
        "Golden Dataset v2 is ready "
        "for retrieval benchmarking."
    )


if __name__ == "__main__":
    main()