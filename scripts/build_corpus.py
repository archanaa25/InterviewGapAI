#!/usr/bin/env python3

"""
Build the master InterviewGap AI corpus.

Input:
    data/prepared/<competency>/
        interview_questions.jsonl
        evaluation_knowledge.jsonl

Output:
    data/prepared/master/
        interview_questions.jsonl
        evaluation_knowledge.jsonl
        corpus_manifest.json

Usage:
    python3 scripts/build_corpus.py
"""

import json
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PREPARED_DIR = PROJECT_ROOT / "data" / "prepared"
MASTER_DIR = PREPARED_DIR / "master"

MASTER_QUESTIONS = MASTER_DIR / "interview_questions.jsonl"
MASTER_EVALUATIONS = MASTER_DIR / "evaluation_knowledge.jsonl"
MANIFEST_FILE = MASTER_DIR / "corpus_manifest.json"


# Competencies expected in the MVP.
# The directory names under data/prepared/ must match these.
EXPECTED_CORPORA = [
    "rag",
    "agentic_ai",
    "llm_fundamentals",
    "ai_evaluation",
    "python_software_engineering",
    "ai_system_design",
    "ai_security",
]


errors = []
warnings = []


def load_jsonl(path):
    """Load a JSONL file into a list of dictionaries."""

    records = []

    if not path.exists():
        errors.append(f"Missing file: {path}")
        return records

    with path.open("r", encoding="utf-8") as f:

        for line_number, line in enumerate(f, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as exc:
                errors.append(
                    f"{path}:{line_number}: "
                    f"invalid JSON: {exc}"
                )
                continue

            if not isinstance(record, dict):
                errors.append(
                    f"{path}:{line_number}: "
                    "record must be a JSON object"
                )
                continue

            records.append(record)

    return records


def find_duplicate_ids(records, id_field):
    """Return duplicate IDs."""

    ids = [
        record.get(id_field)
        for record in records
        if record.get(id_field)
    ]

    counts = Counter(ids)

    return sorted(
        record_id
        for record_id, count in counts.items()
        if count > 1
    )


def validate_global_ids(questions, evaluations):
    """Ensure IDs remain unique after all corpora are merged."""

    duplicate_questions = find_duplicate_ids(
        questions,
        "question_id",
    )

    for qid in duplicate_questions:
        errors.append(
            f"Duplicate global question_id: {qid}"
        )

    duplicate_evaluations = find_duplicate_ids(
        evaluations,
        "evaluation_id",
    )

    for eid in duplicate_evaluations:
        errors.append(
            f"Duplicate global evaluation_id: {eid}"
        )


def validate_references(questions, evaluations):
    """
    Ensure every evaluation_refs entry used by a question
    exists in the master evaluation corpus.
    """

    evaluation_ids = {
        record.get("evaluation_id")
        for record in evaluations
        if record.get("evaluation_id")
    }

    referenced_ids = set()

    for question in questions:

        qid = question.get(
            "question_id",
            "UNKNOWN_QUESTION",
        )

        refs = question.get(
            "evaluation_refs",
            [],
        )

        for ref in refs:

            referenced_ids.add(ref)

            if ref not in evaluation_ids:
                errors.append(
                    f"{qid}: evaluation_ref "
                    f"'{ref}' does not exist "
                    "in master evaluation corpus"
                )

    unused_evaluations = (
        evaluation_ids - referenced_ids
    )

    for eid in sorted(unused_evaluations):
        warnings.append(
            f"Evaluation record is not referenced "
            f"by any question: {eid}"
        )


def validate_roles(questions, evaluations):
    """Report unexpected role values."""

    roles = {
        record.get("role")
        for record in questions + evaluations
        if record.get("role")
    }

    for role in sorted(roles):
        if role != "ai_engineer":
            warnings.append(
                f"Unexpected role in corpus: {role}"
            )


def write_jsonl(records, path):
    """Write records as JSONL."""

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


def build_manifest(
    questions,
    evaluations,
    corpus_stats,
):
    """Create corpus statistics for traceability."""

    difficulty_counts = Counter(
        q.get("difficulty")
        for q in questions
    )

    question_type_counts = Counter(
        q.get("question_type")
        for q in questions
    )

    competency_counts = Counter(
        q.get("competency")
        for q in questions
    )

    sub_competency_counts = Counter(
        q.get("sub_competency")
        for q in questions
    )

    manifest = {
        "role": "ai_engineer",

        "total_questions": len(questions),

        "total_evaluation_records": len(
            evaluations
        ),

        "corpora": corpus_stats,

        "questions_by_competency": dict(
            sorted(competency_counts.items())
        ),

        "questions_by_sub_competency": dict(
            sorted(sub_competency_counts.items())
        ),

        "questions_by_difficulty": {
            "basic": difficulty_counts.get(
                "basic",
                0,
            ),
            "intermediate": difficulty_counts.get(
                "intermediate",
                0,
            ),
            "advanced": difficulty_counts.get(
                "advanced",
                0,
            ),
        },

        "questions_by_type": dict(
            sorted(question_type_counts.items())
        ),
    }

    MANIFEST_FILE.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def print_summary(
    questions,
    evaluations,
    corpus_stats,
):
    """Print useful build statistics."""

    print()
    print("=" * 65)
    print("INTERVIEWGAP AI - MASTER CORPUS BUILD")
    print("=" * 65)

    print()
    print("Corpora")
    print("-------")

    for corpus_name, stats in corpus_stats.items():

        print(
            f"{corpus_name:<30} "
            f"questions={stats['questions']:<4} "
            f"evaluations={stats['evaluations']}"
        )

    print()
    print("TOTAL")
    print("-----")

    print(
        f"Questions          : {len(questions)}"
    )

    print(
        f"Evaluation records : {len(evaluations)}"
    )

    print()
    print("Difficulty")
    print("----------")

    difficulties = Counter(
        q.get("difficulty")
        for q in questions
    )

    for difficulty in [
        "basic",
        "intermediate",
        "advanced",
    ]:

        print(
            f"{difficulty:<15}: "
            f"{difficulties.get(difficulty, 0)}"
        )

    print()
    print("Question Types")
    print("--------------")

    types = Counter(
        q.get("question_type")
        for q in questions
    )

    for name, count in sorted(types.items()):

        print(
            f"{name:<18}: {count}"
        )

    print()
    print("Competencies")
    print("------------")

    competencies = Counter(
        q.get("competency")
        for q in questions
    )

    for name, count in sorted(
        competencies.items()
    ):

        print(
            f"{name:<30}: {count}"
        )


def main():

    all_questions = []
    all_evaluations = []

    corpus_stats = {}

    print(
        "Building InterviewGap AI master corpus..."
    )

    for corpus_name in EXPECTED_CORPORA:

        corpus_dir = (
            PREPARED_DIR
            / corpus_name
        )

        question_file = (
            corpus_dir
            / "interview_questions.jsonl"
        )

        evaluation_file = (
            corpus_dir
            / "evaluation_knowledge.jsonl"
        )

        print()
        print(
            f"Loading: {corpus_name}"
        )

        questions = load_jsonl(
            question_file
        )

        evaluations = load_jsonl(
            evaluation_file
        )

        corpus_stats[corpus_name] = {
            "questions": len(questions),
            "evaluations": len(evaluations),
        }

        all_questions.extend(
            questions
        )

        all_evaluations.extend(
            evaluations
        )

    #
    # Stop immediately if source files
    # could not be loaded correctly.
    #
    if errors:

        print()
        print("BUILD FAILED")
        print("------------")

        for error in errors:
            print(
                f"ERROR: {error}"
            )

        sys.exit(1)

    #
    # Global validation
    #
    validate_global_ids(
        all_questions,
        all_evaluations,
    )

    validate_references(
        all_questions,
        all_evaluations,
    )

    validate_roles(
        all_questions,
        all_evaluations,
    )

    print_summary(
        all_questions,
        all_evaluations,
        corpus_stats,
    )

    #
    # Warnings do not block build.
    #
    if warnings:

        print()
        print("WARNINGS")
        print("--------")

        for warning in warnings:
            print(
                f"WARNING: {warning}"
            )

    #
    # Errors DO block build.
    #
    if errors:

        print()
        print("BUILD FAILED")
        print("------------")

        for error in errors:
            print(
                f"ERROR: {error}"
            )

        print()
        print(
            f"{len(errors)} error(s) found."
        )

        sys.exit(1)

    #
    # Deterministic ordering makes
    # diffs/rebuilds easier.
    #
    all_questions.sort(
        key=lambda x: x.get(
            "question_id",
            "",
        )
    )

    all_evaluations.sort(
        key=lambda x: x.get(
            "evaluation_id",
            "",
        )
    )

    #
    # Write master corpus.
    #
    MASTER_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_jsonl(
        all_questions,
        MASTER_QUESTIONS,
    )

    write_jsonl(
        all_evaluations,
        MASTER_EVALUATIONS,
    )

    build_manifest(
        all_questions,
        all_evaluations,
        corpus_stats,
    )

    print()
    print("BUILD PASSED")

    print()
    print("Master corpus created:")
    print(
        f"  {MASTER_QUESTIONS}"
    )
    print(
        f"  {MASTER_EVALUATIONS}"
    )
    print(
        f"  {MANIFEST_FILE}"
    )


if __name__ == "__main__":
    main()
