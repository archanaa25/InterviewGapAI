"""
Smoke test for Interview Agent question selection.

Runs a saved interview plan through live Question RAG and prints the ten
questions the Interview Agent would ask.

Usage:
    uv run python scripts/test_question_selector.py [candidate_01]
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.interview.question_selector import select_interview_questions
from src.schemas.interview_plan import InterviewPlan


PLAN_DIR = PROJECT_ROOT / "data" / "prepared" / "interview_plans"


def main():

    candidate_id = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "candidate_01"
    )

    plan_path = PLAN_DIR / f"{candidate_id}_plan.json"

    plan = InterviewPlan.model_validate(
        json.loads(
            plan_path.read_text(encoding="utf-8")
        )
    )

    question_set = select_interview_questions(plan)

    print("=" * 70)
    print("INTERVIEW QUESTION SELECTION")
    print("=" * 70)
    print(f"Candidate : {question_set.candidate_id}")
    print(f"Questions : {len(question_set.questions)}")
    print(f"Complete  : {question_set.is_complete}")

    for question in question_set.questions:

        relaxed = (
            "  [difficulty relaxed]"
            if question.retrieval.filter_relaxed
            else ""
        )

        print()
        print(
            f"{question.position:>2}. "
            f"{question.question_id} "
            f"({question.competency.value} / "
            f"{question.difficulty}) "
            f"score={question.retrieval.score:.4f}"
            f"{relaxed}"
        )

        print(f"    {question.question}")

        print(
            f"    must-have: "
            f"{', '.join(question.expected_concepts.must_have)}"
        )

    for slot in question_set.unfilled_slots:
        print()
        print(f"UNFILLED: {slot.reason}")

    for warning in question_set.warnings:
        print()
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()
