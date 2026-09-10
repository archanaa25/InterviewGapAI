from enum import Enum

from pydantic import BaseModel, Field


class CoverageLevel(str, Enum):
    COVERED = "COVERED"
    PARTIAL = "PARTIAL"
    NOT_COVERED = "NOT_COVERED"


class ConceptCoverageResult(BaseModel):
    question_id: str

    concept: str

    coverage: CoverageLevel

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )

    reason: str = Field(
        ...,
        min_length=1,
    )
