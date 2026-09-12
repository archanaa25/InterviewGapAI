"""Deterministic scoring handoff between the Evaluation Agent and the UI.

The Evaluation Agent deliberately returns no numbers. Every score in this
module is computed by :mod:`src.scoring.scorecard` from accepted concept
judgements, so a score can always be traced back to the concepts that produced
it.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field, model_validator

from src.schemas.answer_evaluation import QuestionEvaluationStatus
from src.schemas.resume_analysis import Competency


# A competency at or above this percentage reads as a strength. The learning
# catalog carries the same threshold so the results screen and the resource
# catalog can never disagree about what counts as a gap.
DEFAULT_COMPETENCY_THRESHOLD = 70.0


class ScoreBand(str, Enum):
    """Plain-language band for one score, used for colour and copy."""

    STRONG = "STRONG"
    DEVELOPING = "DEVELOPING"
    GAP = "GAP"
    NOT_SCORED = "NOT_SCORED"


class QuestionScore(BaseModel):
    """One question's contribution to the scorecard."""

    question_id: str = Field(..., min_length=1)
    competency: Competency
    status: QuestionEvaluationStatus
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="None only when the question was excluded from scoring.",
    )
    scored: bool = Field(
        ...,
        description="False for NEEDS_REVIEW: a technical failure is never a zero.",
    )
    demonstrated_count: int = Field(default=0, ge=0)
    partial_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    bonus_concepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_scored_state(self):
        """A scored question has a number; an excluded one never does."""

        if self.scored and self.score is None:
            raise ValueError("A scored question needs a score.")
        if not self.scored and self.score is not None:
            raise ValueError("An excluded question cannot carry a score.")
        return self


class CompetencyScore(BaseModel):
    """Aggregate for one competency across the questions that assessed it."""

    competency: Competency
    score: float | None = Field(default=None, ge=0.0, le=100.0)
    band: ScoreBand
    question_count: int = Field(..., ge=1)
    scored_count: int = Field(..., ge=0)
    skipped_count: int = Field(default=0, ge=0)
    review_count: int = Field(default=0, ge=0)
    demonstrated_count: int = Field(default=0, ge=0)
    partial_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    strong_concepts: List[str] = Field(
        default_factory=list,
        description="Must-have concepts the candidate demonstrated.",
    )
    missing_concepts: List[str] = Field(
        default_factory=list,
        description="Must-have concepts the candidate missed or only part-met.",
    )
    bonus_concepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_band(self):
        """An unscored competency is the only one without a number."""

        if (self.score is None) != (self.band == ScoreBand.NOT_SCORED):
            raise ValueError("Only a NOT_SCORED competency may omit its score.")
        return self


class InterviewScorecard(BaseModel):
    """Deterministic scores derived from one validated InterviewEvaluation."""

    candidate_id: str = Field(..., min_length=1)
    overall_score: float | None = Field(default=None, ge=0.0, le=100.0)
    band: ScoreBand
    threshold: float = Field(default=DEFAULT_COMPETENCY_THRESHOLD, ge=0.0, le=100.0)
    questions: List[QuestionScore]
    competencies: List[CompetencyScore]
    answered_count: int = Field(..., ge=0)
    skipped_count: int = Field(..., ge=0)
    review_count: int = Field(..., ge=0)

    @property
    def scored_count(self) -> int:
        """Questions that carry a number, skips included."""

        return sum(question.scored for question in self.questions)

    @property
    def strengths(self) -> List[CompetencyScore]:
        """Scored competencies at or above the threshold, strongest first."""

        return sorted(
            (
                competency
                for competency in self.competencies
                if competency.score is not None and competency.score >= self.threshold
            ),
            key=lambda competency: competency.score,
            reverse=True,
        )

    @property
    def gaps(self) -> List[CompetencyScore]:
        """Scored competencies below the threshold, weakest first."""

        return sorted(
            (
                competency
                for competency in self.competencies
                if competency.score is not None and competency.score < self.threshold
            ),
            key=lambda competency: competency.score,
        )

    @property
    def ranked_competencies(self) -> List[CompetencyScore]:
        """Every competency weakest first; unscored ones sort last."""

        return sorted(
            self.competencies,
            key=lambda competency: (
                competency.score is None,
                competency.score if competency.score is not None else 0.0,
            ),
        )


__all__ = [
    "CompetencyScore",
    "DEFAULT_COMPETENCY_THRESHOLD",
    "InterviewScorecard",
    "QuestionScore",
    "ScoreBand",
]
