"""
Selected interview question contract for InterviewGapAI.

An InterviewPlan states which competencies and difficulties to test.
This module describes the concrete questions chosen to satisfy that plan.

IMPORTANT DESIGN PRINCIPLE
--------------------------
Pinecone question metadata does not carry expected_concepts or
evaluation_refs. Every selected question is resolved back to its master
corpus record so the Evaluation Agent grades against curated concepts
rather than retrieval metadata.
"""

from typing import List

from pydantic import BaseModel, Field, model_validator

from src.schemas.resume_analysis import Competency


class RetrievalTrace(BaseModel):
    """How one question was chosen, kept for traceability and debugging."""

    query: str = Field(
        ...,
        min_length=1,
        description="Natural-language text sent to Question RAG.",
    )

    score: float = Field(
        ...,
        description=(
            "Vector similarity score. Not a question-quality measure."
        ),
    )

    rank: int = Field(
        ...,
        ge=1,
        description="One-based rank within its retrieval call.",
    )

    requested_difficulty: str = Field(
        ...,
        description="Difficulty the interview plan asked for.",
    )

    filter_relaxed: bool = Field(
        default=False,
        description=(
            "True when the requested difficulty pool was exhausted and "
            "the question came from another difficulty in the same "
            "competency."
        ),
    )


class ExpectedConcepts(BaseModel):
    """Curated grading concepts copied from the master corpus record."""

    must_have: List[str] = Field(default_factory=list)

    bonus: List[str] = Field(default_factory=list)


class SelectedQuestion(BaseModel):
    """One corpus question assigned to one interview slot."""

    position: int = Field(
        ...,
        ge=1,
        description="Order in which the question is asked.",
    )

    question_id: str = Field(..., min_length=1)

    competency: Competency

    sub_competency: str | None = None

    difficulty: str

    question_type: str | None = None

    question: str = Field(..., min_length=1)

    expected_concepts: ExpectedConcepts

    evaluation_refs: List[str] = Field(
        default_factory=list,
        description=(
            "Curated evaluation knowledge IDs linked to this question. "
            "Useful for checking Evaluation RAG retrieval, not a "
            "replacement for it."
        ),
    )

    plan_reason: str = Field(
        ...,
        min_length=1,
        description="Why the plan allocated this competency slot.",
    )

    retrieval: RetrievalTrace


class UnfilledSlot(BaseModel):
    """A plan slot the corpus could not satisfy."""

    competency: Competency

    difficulty: str

    count: int = Field(..., ge=1)

    reason: str = Field(..., min_length=1)


class InterviewQuestionSet(BaseModel):
    """The executable interview: plan slots resolved to corpus questions."""

    candidate_id: str = Field(..., min_length=1)

    questions: List[SelectedQuestion]

    unfilled_slots: List[UnfilledSlot] = Field(default_factory=list)

    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal problems, such as a retrieved question_id missing "
            "from the master corpus."
        ),
    )

    @model_validator(mode="after")
    def validate_questions(self):

        # A repeated question wastes an interview slot and double-counts one
        # competency during scoring, so reject it rather than warn.
        question_ids = [
            question.question_id
            for question in self.questions
        ]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Duplicate question_id found in interview question set."
            )

        # Positions are the asking order the session state machine relies on.
        positions = [
            question.position
            for question in self.questions
        ]

        if positions != list(range(1, len(positions) + 1)):
            raise ValueError(
                "Question positions must be consecutive starting at 1."
            )

        return self

    @property
    def is_complete(self) -> bool:
        """True when every plan slot was filled."""

        return not self.unfilled_slots
