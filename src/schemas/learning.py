"""Curated learning resources matched to a candidate's competency scores."""

from typing import Dict, List

from pydantic import BaseModel, Field, HttpUrl

from src.schemas.resume_analysis import Competency
from src.schemas.scorecard import ScoreBand


class LearningResource(BaseModel):
    """One curated resource from the contributor-owned catalog."""

    resource_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    authors: List[str] = Field(default_factory=list)
    type: str = Field(..., min_length=1)
    url: HttpUrl
    free: bool = True
    priority: int = Field(default=99, ge=1)
    note: str | None = Field(
        default=None,
        description="Standing detail such as a cohort date or price.",
    )


class CompetencyResources(BaseModel):
    """The catalog's entry for one competency."""

    display_name: str = Field(..., min_length=1)
    resources: List[LearningResource] = Field(default_factory=list)


class RecommendationConfig(BaseModel):
    """Catalog-owned thresholds, so policy lives beside the resources."""

    competency_threshold: float = Field(default=70.0, ge=0.0, le=100.0)
    max_resources_per_competency: int = Field(default=3, ge=1)


class FeaturedPerson(BaseModel):
    """One person or organisation worth following, with no score attached."""

    name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    url: HttpUrl


class FeaturedSection(BaseModel):
    """Standing recommendations shown to every candidate.

    These are not matched to a score. They sit at the end of the plan as
    "where to go next" rather than "what you got wrong", so they must never
    displace the gap-driven resources above them.
    """

    title: str = Field(..., min_length=1)
    subtitle: str | None = None
    highlight: LearningResource | None = None
    people: List[FeaturedPerson] = Field(default_factory=list)
    reading: List[LearningResource] = Field(default_factory=list)
    community: FeaturedPerson | None = None


class LearningCatalog(BaseModel):
    """Full curated catalog as stored on disk."""

    version: str = "1.0"
    last_updated: str | None = None
    description: str | None = None
    recommendation_config: RecommendationConfig = Field(
        default_factory=RecommendationConfig
    )
    competencies: Dict[Competency, CompetencyResources] = Field(default_factory=dict)
    featured: FeaturedSection | None = None


class LearningRecommendation(BaseModel):
    """Resources for one competency, with the score that motivated them."""

    competency: Competency
    display_name: str = Field(..., min_length=1)
    score: float | None = Field(default=None, ge=0.0, le=100.0)
    band: ScoreBand
    is_priority: bool = Field(
        ...,
        description="True when the competency scored below the catalog threshold.",
    )
    reason: str = Field(..., min_length=1)
    focus_concepts: List[str] = Field(
        default_factory=list,
        description="Must-have concepts the answers missed, to aim the study at.",
    )
    resources: List[LearningResource] = Field(default_factory=list)


class LearningPlan(BaseModel):
    """Every assessed competency, weakest first, with curated next steps."""

    candidate_id: str = Field(..., min_length=1)
    threshold: float = Field(default=70.0, ge=0.0, le=100.0)
    recommendations: List[LearningRecommendation] = Field(default_factory=list)
    featured: FeaturedSection | None = None

    @property
    def priority_count(self) -> int:
        """How many competencies fell below the catalog threshold."""

        return sum(item.is_priority for item in self.recommendations)


__all__ = [
    "CompetencyResources",
    "FeaturedPerson",
    "FeaturedSection",
    "LearningCatalog",
    "LearningPlan",
    "LearningRecommendation",
    "LearningResource",
    "RecommendationConfig",
]
