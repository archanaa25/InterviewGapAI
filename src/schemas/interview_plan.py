"""
Interview Plan Schema for InterviewGapAI.

The plan specifies both:
1. Which competencies should be tested.
2. What difficulty should be used for each competency.

This produces executable retrieval requirements for Question RAG.
"""

from typing import List

from pydantic import BaseModel, Field, model_validator

from src.schemas.resume_analysis import Competency


class CompetencyTarget(BaseModel):
    """Question and difficulty allocation for one competency."""

    competency: Competency = Field(
        ...,
        description="Competency to probe during the interview.",
    )

    basic: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of basic questions.",
    )

    intermediate: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of intermediate questions.",
    )

    advanced: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of advanced questions.",
    )

    reason: str = Field(
        ...,
        min_length=1,
        description="Reason for this competency and difficulty allocation.",
    )

    @property
    def question_count(self) -> int:
        # Derive the count from difficulty allocations so it cannot drift from
        # the number of retrieval slots requested for this competency.
        return self.basic + self.intermediate + self.advanced


class DifficultyDistribution(BaseModel):
    """Overall difficulty distribution for the interview."""

    basic: int = Field(default=0, ge=0, le=10)
    intermediate: int = Field(default=0, ge=0, le=10)
    advanced: int = Field(default=0, ge=0, le=10)

    @model_validator(mode="after")
    def validate_total(self):

        total = (
            self.basic
            + self.intermediate
            + self.advanced
        )

        if total != 10:
            raise ValueError(
                f"Difficulty distribution must total 10; got {total}"
            )

        return self


class InterviewStrategy(BaseModel):
    """High-level strategy for constructing the interview."""

    validate_claimed_strengths: bool = True
    probe_unknown_areas: bool = True
    avoid_resume_based_negative_assumptions: bool = True

    rationale: str = Field(
        ...,
        min_length=1,
        description="Overall rationale for the interview strategy.",
    )


class InterviewPlan(BaseModel):
    """Structured 10-question interview plan."""

    candidate_id: str = Field(
        ...,
        min_length=1,
    )

    total_questions: int = Field(
        default=10,
        ge=10,
        le=10,
    )

    competency_targets: List[CompetencyTarget] = Field(
        ...,
        description=(
            "Question and difficulty allocation "
            "for each selected competency."
        ),
    )

    difficulty_distribution: DifficultyDistribution

    strategy: InterviewStrategy

    @model_validator(mode="after")
    def validate_plan(self):

        # -----------------------------------
        # 1. Validate total question count
        # -----------------------------------

        # Cross-field rules run after individual fields have been validated.
        # Valid field types alone cannot guarantee a ten-question plan.
        allocated = sum(
            target.question_count
            for target in self.competency_targets
        )

        if allocated != self.total_questions:
            raise ValueError(
                f"Competency allocation must total "
                f"{self.total_questions}; got {allocated}"
            )

        # -----------------------------------
        # 2. Validate duplicate competencies
        # -----------------------------------

        competencies = [
            target.competency
            for target in self.competency_targets
        ]

        if len(competencies) != len(set(competencies)):
            raise ValueError(
                "Duplicate competencies found in interview plan."
            )

        # -----------------------------------
        # 3. Calculate difficulty totals from
        #    competency allocations
        # -----------------------------------

        basic_total = sum(
            target.basic
            for target in self.competency_targets
        )

        intermediate_total = sum(
            target.intermediate
            for target in self.competency_targets
        )

        advanced_total = sum(
            target.advanced
            for target in self.competency_targets
        )

        # -----------------------------------
        # 4. Verify matrix matches global
        #    difficulty distribution
        # -----------------------------------

        # The summary distribution must agree with the per-competency counts:
        # downstream retrieval uses those detailed counts to select questions.
        if basic_total != self.difficulty_distribution.basic:
            raise ValueError(
                "Basic question allocation does not match "
                "difficulty_distribution."
            )

        if (
            intermediate_total
            != self.difficulty_distribution.intermediate
        ):
            raise ValueError(
                "Intermediate question allocation does not match "
                "difficulty_distribution."
            )

        if advanced_total != self.difficulty_distribution.advanced:
            raise ValueError(
                "Advanced question allocation does not match "
                "difficulty_distribution."
            )

        return self