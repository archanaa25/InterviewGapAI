#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from collections import Counter


PROJECT_ROOT = Path(__file__).resolve().parent.parent


if len(sys.argv) != 2:
    print(
        "Usage: python3 scripts/validate_corpus.py "
        "<competency>"
    )
    print()
    print("Examples:")
    print(
        "  python3 scripts/validate_corpus.py rag"
    )
    print(
        "  python3 scripts/validate_corpus.py agentic_ai"
    )
    sys.exit(1)


CORPUS_NAME = sys.argv[1]

CURATED_DIR = (
    PROJECT_ROOT
    / "data"
    / "curated"
    / CORPUS_NAME
)

QUESTION_FILE = (
    CURATED_DIR
    / f"{CORPUS_NAME}_questions.json"
)

EVALUATION_FILE = (
    CURATED_DIR
    / f"{CORPUS_NAME}_evaluation_knowledge.json"
)

PREPARED_DIR = (
    PROJECT_ROOT
    / "data"
    / "prepared"
    / CORPUS_NAME
)

QUESTION_JSONL = (
    PREPARED_DIR
    / "interview_questions.jsonl"
)

EVALUATION_JSONL = (
    PREPARED_DIR
    / "evaluation_knowledge.jsonl"
)

# QUESTION_FILE = (
#     PROJECT_ROOT
#     / "data/curated/rag_questions.json"
# )

# EVALUATION_FILE = (
#     PROJECT_ROOT
#     / "data/curated/rag_evaluation_knowledge.json"
# )

# PREPARED_DIR = PROJECT_ROOT / "data/prepared"

# QUESTION_JSONL = PREPARED_DIR / "interview_questions.jsonl"
# EVALUATION_JSONL = PREPARED_DIR / "evaluation_knowledge.jsonl"


VALID_DIFFICULTIES = {
    "basic",
    "intermediate",
    "advanced",
}

VALID_QUESTION_TYPES = {
    "conceptual",
    "scenario",
    "design",
    "troubleshooting",
}

VALID_ROLES = {
    "ai_engineer",
}

VALID_COMPETENCIES = {
    "python_software_engineering",
    "ai_ml_llm_fundamentals",
    "prompt_engineering",
    "rag",
    "agentic_ai",
    "ai_evaluation",
    "ai_system_design",
    "deployment_llmops",
    "ai_security",
    "problem_solving",
}


errors = []
warnings = []


def load_json(path):
    if not path.exists():
        errors.append(f"File does not exist: {path}")
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        errors.append(
            f"Invalid JSON in {path}: "
            f"line {exc.lineno}, column {exc.colno}"
        )
        return []

    if not isinstance(data, list):
        errors.append(
            f"{path} must contain a JSON array."
        )
        return []

    return data


def check_required_fields(record, fields, record_id):
    for field in fields:
        if field not in record:
            errors.append(
                f"{record_id}: missing required field '{field}'"
            )


def check_unique_ids(records, id_field, label):
    ids = [
        r.get(id_field)
        for r in records
        if r.get(id_field)
    ]

    duplicates = [
        item
        for item, count in Counter(ids).items()
        if count > 1
    ]

    for duplicate in duplicates:
        errors.append(
            f"Duplicate {label}: {duplicate}"
        )


def validate_questions(questions):
    required_fields = [
        "question_id",
        "role",
        "competency",
        "sub_competency",
        "difficulty",
        "question_type",
        "question",
        "expected_concepts",
        "evaluation_refs",
        "tags",
    ]

    for q in questions:
        qid = q.get("question_id", "UNKNOWN_QUESTION")

        check_required_fields(
            q,
            required_fields,
            qid,
        )

        if q.get("role") not in VALID_ROLES:
            errors.append(
                f"{qid}: invalid role '{q.get('role')}'"
            )

        if q.get("competency") not in VALID_COMPETENCIES:
            errors.append(
                f"{qid}: invalid competency "
                f"'{q.get('competency')}'"
            )

        if q.get("difficulty") not in VALID_DIFFICULTIES:
            errors.append(
                f"{qid}: invalid difficulty "
                f"'{q.get('difficulty')}'"
            )

        if q.get("question_type") not in VALID_QUESTION_TYPES:
            errors.append(
                f"{qid}: invalid question_type "
                f"'{q.get('question_type')}'"
            )

        if not q.get("question", "").strip():
            errors.append(
                f"{qid}: question cannot be empty"
            )

        expected = q.get("expected_concepts", {})

        if not isinstance(expected, dict):
            errors.append(
                f"{qid}: expected_concepts must be an object"
            )
            continue

        must_have = expected.get("must_have")
        bonus = expected.get("bonus")

        if not isinstance(must_have, list) or not must_have:
            errors.append(
                f"{qid}: must_have must be a non-empty list"
            )

        if not isinstance(bonus, list):
            errors.append(
                f"{qid}: bonus must be a list"
            )

        refs = q.get("evaluation_refs")

        if not isinstance(refs, list) or not refs:
            errors.append(
                f"{qid}: evaluation_refs must be "
                "a non-empty list"
            )

        tags = q.get("tags")

        if not isinstance(tags, list) or not tags:
            warnings.append(
                f"{qid}: no tags configured"
            )

    check_unique_ids(
        questions,
        "question_id",
        "question_id",
    )


def validate_evaluation_knowledge(records):
    required_fields = [
        "evaluation_id",
        "role",
        "competency",
        "sub_competency",
        "topic",
        "content",
        "key_concepts",
        "common_misconceptions",
        "source",
        "tags",
    ]

    for record in records:
        eid = record.get(
            "evaluation_id",
            "UNKNOWN_EVALUATION",
        )

        check_required_fields(
            record,
            required_fields,
            eid,
        )

        if record.get("role") not in VALID_ROLES:
            errors.append(
                f"{eid}: invalid role "
                f"'{record.get('role')}'"
            )

        if record.get("competency") not in VALID_COMPETENCIES:
            errors.append(
                f"{eid}: invalid competency "
                f"'{record.get('competency')}'"
            )

        if not record.get("content", "").strip():
            errors.append(
                f"{eid}: content cannot be empty"
            )

        key_concepts = record.get("key_concepts")

        if (
            not isinstance(key_concepts, list)
            or not key_concepts
        ):
            errors.append(
                f"{eid}: key_concepts must be "
                "a non-empty list"
            )

        misconceptions = record.get(
            "common_misconceptions"
        )

        if not isinstance(misconceptions, list):
            errors.append(
                f"{eid}: common_misconceptions "
                "must be a list"
            )

        source = record.get("source")

        if not isinstance(source, dict):
            errors.append(
                f"{eid}: source must be an object"
            )

    check_unique_ids(
        records,
        "evaluation_id",
        "evaluation_id",
    )


def validate_references(questions, evaluation_records):
    evaluation_ids = {
        r.get("evaluation_id")
        for r in evaluation_records
        if r.get("evaluation_id")
    }

    used_refs = set()

    for question in questions:
        qid = question.get(
            "question_id",
            "UNKNOWN_QUESTION",
        )

        for ref in question.get("evaluation_refs", []):
            used_refs.add(ref)

            if ref not in evaluation_ids:
                errors.append(
                    f"{qid}: evaluation_ref "
                    f"'{ref}' does not exist"
                )

    unused = evaluation_ids - used_refs

    for ref in sorted(unused):
        warnings.append(
            f"Evaluation record not referenced "
            f"by any question: {ref}"
        )


def check_question_duplicates(questions):
    normalized = {}

    for q in questions:
        qid = q.get("question_id", "UNKNOWN")

        text = (
            q.get("question", "")
            .lower()
            .strip()
        )

        text = " ".join(text.split())

        if text in normalized:
            errors.append(
                f"Duplicate question text: "
                f"{qid} and {normalized[text]}"
            )
        else:
            normalized[text] = qid


def write_jsonl(records, path):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )


def print_summary(questions, evaluations):
    print()
    print("=" * 60)
    print("INTERVIEWGAP AI CORPUS VALIDATION")
    print("=" * 60)

    print(f"Questions              : {len(questions)}")
    print(f"Evaluation records     : {len(evaluations)}")

    difficulties = Counter(
        q.get("difficulty")
        for q in questions
    )

    print()
    print("Question difficulty")
    print("-------------------")

    for difficulty in [
        "basic",
        "intermediate",
        "advanced",
    ]:
        print(
            f"{difficulty:<15}: "
            f"{difficulties.get(difficulty, 0)}"
        )

    question_types = Counter(
        q.get("question_type")
        for q in questions
    )

    print()
    print("Question types")
    print("--------------")

    for question_type, count in sorted(
        question_types.items()
    ):
        print(
            f"{question_type:<15}: {count}"
        )

    sub_competencies = Counter(
        q.get("sub_competency")
        for q in questions
    )

    print()
    print("Questions by sub-competency")
    print("---------------------------")

    for name, count in sorted(
        sub_competencies.items()
    ):
        print(
            f"{name:<25}: {count}"
        )


def main():
    questions = load_json(QUESTION_FILE)
    evaluations = load_json(EVALUATION_FILE)

    if errors:
        print("\n".join(errors))
        sys.exit(1)

    validate_questions(questions)

    validate_evaluation_knowledge(
        evaluations
    )

    validate_references(
        questions,
        evaluations,
    )

    check_question_duplicates(
        questions
    )

    print_summary(
        questions,
        evaluations,
    )

    if warnings:
        print()
        print("WARNINGS")
        print("--------")

        for warning in warnings:
            print(f"WARNING: {warning}")

    if errors:
        print()
        print("VALIDATION FAILED")
        print("-----------------")

        for error in errors:
            print(f"ERROR: {error}")

        print()
        print(
            f"{len(errors)} validation error(s) found."
        )

        sys.exit(1)

    print()
    print("VALIDATION PASSED")

    write_jsonl(
        questions,
        QUESTION_JSONL,
    )

    write_jsonl(
        evaluations,
        EVALUATION_JSONL,
    )

    print()
    print("Prepared files:")
    print(f"  {QUESTION_JSONL}")
    print(f"  {EVALUATION_JSONL}")


if __name__ == "__main__":
    main()
