"""Validated handoff from the Evaluation Agent to scoring and reporting."""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field, model_validator

from src.schemas.resume_analysis import Competency


class ConceptJudgementStatus(str, Enum):
    """What the submitted answer demonstrated for one required concept."""

    DEMONSTRATED = "DEMONSTRATED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


class QuestionEvaluationStatus(str, Enum):
    """Terminal state of one answer-evaluation attempt."""

    EVALUATED = "EVALUATED"
    SKIPPED = "SKIPPED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ReviewReason(str, Enum):
    """Candidate-safe reason why an answer could not be evaluated."""

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


class ConceptJudgement(BaseModel):
    """Grounded model judgement for one exact must-have concept."""

    concept: str = Field(..., min_length=1)
    status: ConceptJudgementStatus
    rationale: str = Field(..., min_length=1)
    answer_excerpt: str | None = None
    evidence_ids: List[str] = Field(default_factory=list)


class AnswerAssessmentDraft(BaseModel):
    """Structured LLM output validated by the agent before it is accepted."""

    concept_judgements: List[ConceptJudgement]
    bonus_concepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class RetrievedEvidenceReference(BaseModel):
    """Retrieval provenance retained without duplicating rubric content."""

    evaluation_id: str = Field(..., min_length=1)
    rank: int = Field(..., ge=1)
    similarity_score: float = Field(
        ...,
        description="Vector similarity, not a candidate grade or confidence.",
    )


class QuestionEvaluation(BaseModel):
    """One terminal evaluation ready for deterministic scoring."""

    question_id: str = Field(..., min_length=1)
    competency: Competency
    status: QuestionEvaluationStatus
    concept_judgements: List[ConceptJudgement] = Field(default_factory=list)
    bonus_concepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieved_evidence: List[RetrievedEvidenceReference] = Field(default_factory=list)
    attempt_count: int = Field(default=0, ge=0)
    review_reason: ReviewReason | None = None

    @model_validator(mode="after")
    def validate_terminal_state(self):
        """Keep evaluated and non-evaluated records unambiguous."""

        if self.status == QuestionEvaluationStatus.EVALUATED:
            if not self.concept_judgements or self.confidence is None:
                raise ValueError(
                    "An evaluated answer needs concept judgements and confidence."
                )
            if self.review_reason is not None:
                raise ValueError("An evaluated answer cannot have a review reason.")
        elif self.concept_judgements or self.confidence is not None:
            raise ValueError(
                "Skipped or review-required answers cannot contain accepted judgements."
            )

        if (
            self.status == QuestionEvaluationStatus.NEEDS_REVIEW
            and self.review_reason is None
        ):
            raise ValueError("A review-required answer needs a review reason.")

        return self


class InterviewEvaluation(BaseModel):
    """Ordered concept-level evaluations for one submitted interview."""

    candidate_id: str = Field(..., min_length=1)
    questions: List[QuestionEvaluation]

    @model_validator(mode="after")
    def validate_question_ids(self):
        """A submitted question must produce exactly one terminal record."""

        question_ids = [question.question_id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Duplicate question_id found in interview evaluation.")
        return self

    @property
    def evaluated_count(self) -> int:
        """Count answers with accepted concept judgements."""

        return sum(
            question.status == QuestionEvaluationStatus.EVALUATED
            for question in self.questions
        )

    @property
    def skipped_count(self) -> int:
        """Count explicitly skipped answers."""

        return sum(
            question.status == QuestionEvaluationStatus.SKIPPED
            for question in self.questions
        )

    @property
    def review_count(self) -> int:
        """Count technical or evidence failures requiring review."""

        return sum(
            question.status == QuestionEvaluationStatus.NEEDS_REVIEW
            for question in self.questions
        )


__all__ = [
    "AnswerAssessmentDraft",
    "ConceptJudgement",
    "ConceptJudgementStatus",
    "InterviewEvaluation",
    "QuestionEvaluation",
    "QuestionEvaluationStatus",
    "RetrievedEvidenceReference",
    "ReviewReason",
]
