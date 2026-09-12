"""Match curated learning resources to a candidate's competency scores.

Like scoring, this layer is deterministic. The catalog is contributor-owned
data, and the only judgement made here is ordering: weakest competency first,
so the candidate reads their biggest gap before their smallest.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.schemas.learning import (
    LearningCatalog,
    LearningPlan,
    LearningRecommendation,
    LearningResource,
)
from src.schemas.scorecard import InterviewScorecard, ScoreBand


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = PROJECT_ROOT / "data" / "raw" / "learning_resources.json"

BAND_REASONS = {
    ScoreBand.STRONG: "Strong across the concepts we probed. Keep it sharp.",
    ScoreBand.DEVELOPING: "Solid foundation with concepts still to close.",
    ScoreBand.GAP: "Priority gap. Your answers missed core concepts here.",
    ScoreBand.NOT_SCORED: (
        "Not scored in this interview, so treat this as unassessed rather "
        "than weak."
    ),
}

# A competency scores zero when every question in it was skipped, but the
# candidate never claimed anything for it. Telling them their answers "missed
# core concepts" would be untrue, so an unattempted competency says so.
UNATTEMPTED_REASON = (
    "You skipped every question here, so it scores zero. Start from the "
    "basics rather than assuming a gap."
)

# A gap deserves a longer excerpt of what was missed; a strength needs only a
# reminder of where it thinned out.
PRIORITY_CONCEPT_LIMIT = 5
SUPPORTING_CONCEPT_LIMIT = 2


@lru_cache(maxsize=4)
def load_catalog(path: str | None = None) -> LearningCatalog:
    """Load and validate the curated catalog once per path."""

    source = Path(path) if path else CATALOG_PATH
    if not source.exists():
        raise FileNotFoundError(f"Learning catalog not found at {source}.")
    return LearningCatalog.model_validate(json.loads(source.read_text()))


def build_learning_plan(
    scorecard: InterviewScorecard,
    *,
    catalog: LearningCatalog | None = None,
) -> LearningPlan:
    """Recommend resources for every competency, weakest first.

    Every assessed competency appears, so a candidate always leaves with a next
    step. Competencies below the catalog threshold are flagged as priorities
    and sort to the top.
    """

    catalog = catalog or load_catalog()
    limit = catalog.recommendation_config.max_resources_per_competency
    threshold = catalog.recommendation_config.competency_threshold

    recommendations = []
    for competency in scorecard.ranked_competencies:
        entry = catalog.competencies.get(competency.competency)
        if entry is None:
            # A competency with no curated resources is skipped rather than
            # shown empty: an empty section reads as a broken screen.
            continue

        is_priority = (
            competency.score is not None and competency.score < threshold
        )
        unattempted = (
            competency.scored_count > 0
            and competency.skipped_count == competency.scored_count
        )
        concept_limit = (
            PRIORITY_CONCEPT_LIMIT if is_priority else SUPPORTING_CONCEPT_LIMIT
        )
        recommendations.append(
            LearningRecommendation(
                competency=competency.competency,
                display_name=entry.display_name,
                score=competency.score,
                band=competency.band,
                is_priority=is_priority,
                reason=(
                    UNATTEMPTED_REASON
                    if unattempted
                    else BAND_REASONS[competency.band]
                ),
                focus_concepts=competency.missing_concepts[:concept_limit],
                resources=_ranked_resources(entry.resources, limit),
            )
        )

    return LearningPlan(
        candidate_id=scorecard.candidate_id,
        threshold=threshold,
        recommendations=recommendations,
        featured=catalog.featured,
    )


def _ranked_resources(
    resources: list[LearningResource],
    limit: int,
) -> list[LearningResource]:
    """Take the catalog's own priority order, capped at the configured limit."""

    return sorted(resources, key=lambda resource: resource.priority)[:limit]


__all__ = ["BAND_REASONS", "build_learning_plan", "load_catalog"]
