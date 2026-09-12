"""Offline tests for the bounded Evaluation Agent orchestration."""

from collections.abc import Callable
from unittest.mock import patch

import pytest

from src.evaluation.agent import EvaluationAgent, _OpenAIAssessor
from src.schemas.answer_evaluation import (
    AnswerAssessmentDraft,
    ConceptJudgement,
    ConceptJudgementStatus,
    QuestionEvaluationStatus,
    ReviewReason,
)
from src.schemas.interview_questions import (
    ExpectedConcepts,
    InterviewQuestionSet,
    RetrievalTrace,
    SelectedQuestion,
)
from src.schemas.resume_analysis import Competency


def _question(
    question_id: str = "RAG-TEST-001",
    *,
    position: int = 1,
) -> SelectedQuestion:
    return SelectedQuestion(
        position=position,
        question_id=question_id,
        competency=Competency.RAG,
        sub_competency="rag_retrieval",
        difficulty="intermediate",
        question_type="conceptual",
        question="Why can retrieval return irrelevant context?",
        expected_concepts=ExpectedConcepts(
            must_have=["retrieval quality", "metadata filtering"],
            bonus=["reranking"],
        ),
        evaluation_refs=["EVAL-RAG-001"],
        plan_reason="Probe grounded retrieval.",
        retrieval=RetrievalTrace(
            query="grounded retrieval",
            score=0.91,
            rank=1,
            requested_difficulty="intermediate",
        ),
    )


def _context(evaluation_id: str = "EVAL-RAG-001") -> dict:
    return {
        "question": "Why can retrieval return irrelevant context?",
        "competency": "rag",
        "retrieved_knowledge": [
            {
                "evaluation_id": evaluation_id,
                "rank": 1,
                "score": 0.92,
                "content": "Retrieval and metadata filters constrain context quality.",
            }
        ],
    }


def _draft(
    *,
    first_concept: str = "retrieval quality",
    first_evidence: str = "EVAL-RAG-001",
    first_excerpt: str = "retrieval can select irrelevant documents",
) -> AnswerAssessmentDraft:
    return AnswerAssessmentDraft(
        concept_judgements=[
            ConceptJudgement(
                concept=first_concept,
                status=ConceptJudgementStatus.DEMONSTRATED,
                rationale="The answer connects retrieval quality to relevance.",
                answer_excerpt=first_excerpt,
                evidence_ids=[first_evidence],
            ),
            ConceptJudgement(
                concept="metadata filtering",
                status=ConceptJudgementStatus.PARTIAL,
                rationale="Filtering is mentioned without implementation detail.",
                answer_excerpt="metadata filters help",
                evidence_ids=["EVAL-RAG-001"],
            ),
        ],
        bonus_concepts=[],
        misconceptions=[],
        confidence=0.84,
    )


ANSWER = "retrieval can select irrelevant documents; metadata filters help"


def _agent(
    assessor: Callable = lambda *_args: _draft(),
    retrieve: Callable = lambda *_args: _context(),
    *,
    max_attempts: int = 3,
) -> EvaluationAgent:
    return EvaluationAgent(
        retrieve_context=retrieve,
        assessor=assessor,
        max_attempts=max_attempts,
        max_workers=1,
    )


def test_agent_retrieves_and_returns_validated_concept_judgements() -> None:
    """The output is grounded and deliberately contains no score or gap fields."""

    result = _agent().evaluate_question(_question(), ANSWER)

    assert result.status == QuestionEvaluationStatus.EVALUATED
    assert result.attempt_count == 1
    assert result.retrieved_evidence[0].evaluation_id == "EVAL-RAG-001"
    assert result.retrieved_evidence[0].similarity_score == 0.92
    assert [item.concept for item in result.concept_judgements] == [
        "retrieval quality",
        "metadata filtering",
    ]
    assert "score" not in result.model_dump()
    assert "gaps" not in result.model_dump()


def test_blank_answer_is_skipped_without_retrieval_or_model_call() -> None:
    """A deliberate skip is terminal and does not spend external calls."""

    def unexpected(*_args):
        raise AssertionError("No external dependency should be called for a skip.")

    result = _agent(assessor=unexpected, retrieve=unexpected).evaluate_question(
        _question(), "   "
    )

    assert result.status == QuestionEvaluationStatus.SKIPPED
    assert result.attempt_count == 0


def test_missing_linked_rag_evidence_requires_review_without_guessing() -> None:
    """Semantically nearby evidence cannot silently replace the curated link."""

    def unexpected(*_args):
        raise AssertionError("The model must not run on insufficient evidence.")

    result = _agent(
        assessor=unexpected,
        retrieve=lambda *_args: _context("EVAL-UNRELATED"),
    ).evaluate_question(_question(), ANSWER)

    assert result.status == QuestionEvaluationStatus.NEEDS_REVIEW
    assert result.review_reason == ReviewReason.INSUFFICIENT_EVIDENCE
    assert result.confidence is None


def test_invalid_draft_is_repaired_before_it_is_accepted() -> None:
    """Application-owned invariants drive a bounded correction loop."""

    corrections: list[str | None] = []

    def assessor(_question, _answer, _knowledge, correction):
        corrections.append(correction)
        if correction is None:
            return _draft(
                first_concept="invented concept",
                first_evidence="EVAL-INVENTED",
                first_excerpt="words that are not in the answer",
            )
        return _draft()

    result = _agent(assessor=assessor).evaluate_question(_question(), ANSWER)

    assert result.status == QuestionEvaluationStatus.EVALUATED
    assert result.attempt_count == 2
    assert corrections[0] is None
    assert "exactly once" in corrections[1]
    assert "supplied evidence IDs" in corrections[1]
    assert "not copied from the answer" in corrections[1]


def test_exhausted_validation_attempts_become_unscored_review() -> None:
    """Invalid model output never becomes a candidate score by accident."""

    invalid = lambda *_args: _draft(first_concept="wrong concept")
    result = _agent(assessor=invalid, max_attempts=2).evaluate_question(
        _question(), ANSWER
    )

    assert result.status == QuestionEvaluationStatus.NEEDS_REVIEW
    assert result.review_reason == ReviewReason.INVALID_ASSESSMENT
    assert result.attempt_count == 2
    assert result.concept_judgements == []


def test_provider_failure_becomes_review_instead_of_zero() -> None:
    """Technical failure is isolated from candidate performance."""

    def fail(*_args):
        raise RuntimeError("provider response that must not become a score")

    result = _agent(assessor=fail).evaluate_question(_question(), ANSWER)

    assert result.status == QuestionEvaluationStatus.NEEDS_REVIEW
    assert result.review_reason == ReviewReason.TECHNICAL_FAILURE
    assert result.concept_judgements == []


def test_interview_requires_exact_answer_ids_and_preserves_question_order() -> None:
    """The frozen interview is the authority for identity and output order."""

    questions = InterviewQuestionSet(
        candidate_id="candidate-test",
        questions=[
            _question("RAG-TEST-001", position=1),
            _question("RAG-TEST-002", position=2),
        ],
    )
    agent = _agent()

    with pytest.raises(ValueError, match="exactly"):
        agent.evaluate_interview(questions, {"RAG-TEST-001": ANSWER})

    result = agent.evaluate_interview(
        questions,
        {"RAG-TEST-002": ANSWER, "RAG-TEST-001": ANSWER},
    )

    assert [item.question_id for item in result.questions] == [
        "RAG-TEST-001",
        "RAG-TEST-002",
    ]
    assert result.evaluated_count == 2
    assert result.skipped_count == 0
    assert result.review_count == 0


def test_non_positive_agent_limits_are_rejected() -> None:
    """Configuration cannot disable the bounded stopping conditions."""

    with pytest.raises(ValueError, match="max_attempts"):
        _agent(max_attempts=0)

    with pytest.raises(ValueError, match="max_workers"):
        EvaluationAgent(
            retrieve_context=lambda *_args: _context(),
            assessor=lambda *_args: _draft(),
            max_workers=0,
        )


def test_blank_model_override_uses_provider_default(monkeypatch) -> None:
    """An optional blank .env field must never reach the API as model=''."""

    monkeypatch.setenv("EVALUATION_AGENT_MODEL", "")
    with patch(
        "src.evaluation.agent.build_client",
        return_value=(object(), "provider-default-model"),
    ):
        assessor = _OpenAIAssessor()

    assert assessor.model == "provider-default-model"
