from enum import Enum

from pydantic import BaseModel, Field


class JudgeAgreement(str, Enum):
    AGREE = "AGREE"
    DISAGREE = "DISAGREE"


class OnlineJudgeVerdict(BaseModel):
    question_id: str

    concept: str

    agreement: JudgeAgreement

    faithfulness_score: int = Field(
        ...,
        ge=1,
        le=5,
    )

    reason: str = Field(
        ...,
        min_length=1,
    )
