"""Run one real selected question through Evaluation RAG and the Evaluation Agent."""

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation import EvaluationAgent
from src.observability import configure_observability, flush_telemetry, request_context
from src.schemas.interview_questions import InterviewQuestionSet


DEFAULT_QUESTION_SET = (
    PROJECT_ROOT
    / "data"
    / "prepared"
    / "interview_questions"
    / "candidate_03_questions.json"
)
DEFAULT_QUESTION_ID = "LLM-TRANS-BAS-001"
DEFAULT_ANSWER = (
    "A Query represents what the current token is looking for. Keys describe "
    "what other tokens offer for matching, and Values carry the information "
    "combined using the resulting attention weights."
)


def parse_args() -> argparse.Namespace:
    """Read an optional real question-set path, question ID, and answer."""

    parser = argparse.ArgumentParser(
        description="Run one grounded InterviewGapAI answer evaluation.",
    )
    parser.add_argument(
        "--question-set",
        type=Path,
        default=DEFAULT_QUESTION_SET,
        help="Path to an InterviewQuestionSet JSON file.",
    )
    parser.add_argument(
        "--question-id",
        default=DEFAULT_QUESTION_ID,
        help="Question ID from that frozen question set.",
    )
    parser.add_argument(
        "--answer",
        default=DEFAULT_ANSWER,
        help="Candidate answer to evaluate.",
    )
    return parser.parse_args()


def load_question(question_set_path: Path, question_id: str):
    """Resolve one real selected question by its Pinecone/corpus identity."""

    question_set = InterviewQuestionSet.model_validate_json(
        question_set_path.read_text(encoding="utf-8")
    )
    for question in question_set.questions:
        if question.question_id == question_id:
            return question_set, question
    raise ValueError(
        f"Question {question_id!r} is not in {question_set_path}."
    )


def main() -> None:
    """Print the exact smoke input and its validated, non-scored output."""

    args = parse_args()
    question_set, question = load_question(args.question_set, args.question_id)

    print("=" * 72)
    print("EVALUATION AGENT INPUT")
    print("=" * 72)
    print(f"candidate_id : {question_set.candidate_id}")
    print(f"question_id  : {question.question_id}")
    print(f"competency   : {question.competency.value}")
    print(f"question     : {question.question}")
    print(f"must_have    : {json.dumps(question.expected_concepts.must_have)}")
    print(f"answer       : {args.answer}")

    with request_context(
        interview_id="evaluation-smoke",
        question_id=question.question_id,
    ):
        result = EvaluationAgent(max_workers=1).evaluate_question(
            question,
            args.answer,
        )

    print("\n" + "=" * 72)
    print("EVALUATION AGENT OUTPUT")
    print("=" * 72)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    configure_observability(stream=sys.stderr)
    try:
        main()
    finally:
        flush_telemetry()
