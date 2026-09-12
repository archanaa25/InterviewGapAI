"""Turn validated concept judgements into per-question and competency scores.

This layer is deliberately deterministic: no model runs here. The Evaluation
Agent decides whether a concept was demonstrated, and this module decides what
that is worth. Keeping the two apart means a score can be recomputed, audited
and changed in policy without re-running an interview.

Scoring policy
--------------
* DEMONSTRATED counts 1.0, PARTIAL 0.5, MISSING 0.0, averaged over the
  question's must-have concepts.
* A SKIPPED answer scores 0 and stays in the denominator, so declining to
  answer can never protect a score.
* A NEEDS_REVIEW answer is excluded from both numerator and denominator. It is
  a retrieval or provider failure, and the candidate must not absorb it.
* Bonus concepts and misconceptions are reported but never move the number, so
  every score stays explainable from the must-have concepts alone.
"""

from __future__ import annotations

from collections import OrderedDict

from src.schemas.answer_evaluation import (
    ConceptJudgementStatus,
    InterviewEvaluation,
    QuestionEvaluation,
    QuestionEvaluationStatus,
)
from src.schemas.scorecard import (
    CompetencyScore,
    DEFAULT_COMPETENCY_THRESHOLD,
    InterviewScorecard,
    QuestionScore,
    ScoreBand,
)


CONCEPT_WEIGHTS = {
    ConceptJudgementStatus.DEMONSTRATED: 1.0,
    ConceptJudgementStatus.PARTIAL: 0.5,
    ConceptJudgementStatus.MISSING: 0.0,
}

# Below this a competency is a gap; a developing band above it gives the
# results screen something honest to say between "gap" and "strength".
DEVELOPING_BAND = 85.0


def score_question(evaluation: QuestionEvaluation) -> QuestionScore:
    """Score one terminal evaluation under the policy above."""

    counts = {status: 0 for status in ConceptJudgementStatus}
    for judgement in evaluation.concept_judgements:
        counts[judgement.status] += 1

    if evaluation.status == QuestionEvaluationStatus.NEEDS_REVIEW:
        scored, score = False, None
    elif evaluation.status == QuestionEvaluationStatus.SKIPPED:
        scored, score = True, 0.0
    else:
        earned = sum(
            CONCEPT_WEIGHTS[judgement.status]
            for judgement in evaluation.concept_judgements
        )
        scored = True
        score = round(earned / len(evaluation.concept_judgements) * 100, 1)

    return QuestionScore(
        question_id=evaluation.question_id,
        competency=evaluation.competency,
        status=evaluation.status,
        score=score,
        scored=scored,
        demonstrated_count=counts[ConceptJudgementStatus.DEMONSTRATED],
        partial_count=counts[ConceptJudgementStatus.PARTIAL],
        missing_count=counts[ConceptJudgementStatus.MISSING],
        bonus_concepts=list(evaluation.bonus_concepts),
        misconceptions=list(evaluation.misconceptions),
    )


def band_for(score: float | None, threshold: float) -> ScoreBand:
    """Map a score to the band that drives results copy and colour."""

    if score is None:
        return ScoreBand.NOT_SCORED
    if score >= DEVELOPING_BAND:
        return ScoreBand.STRONG
    if score >= threshold:
        return ScoreBand.DEVELOPING
    return ScoreBand.GAP


def build_scorecard(
    evaluation: InterviewEvaluation,
    *,
    threshold: float = DEFAULT_COMPETENCY_THRESHOLD,
) -> InterviewScorecard:
    """Derive per-question, per-competency and overall scores.

    The overall score averages question scores rather than competency scores.
    Competencies carry unequal question counts, so averaging competencies would
    let a single-question competency outweigh a four-question one.
    """

    questions = [score_question(item) for item in evaluation.questions]
    by_competency: "OrderedDict[str, list[QuestionEvaluation]]" = OrderedDict()
    for item in evaluation.questions:
        by_competency.setdefault(item.competency.value, []).append(item)

    competencies = [
        _competency_score(items, threshold) for items in by_competency.values()
    ]

    scored = [question.score for question in questions if question.scored]
    overall = round(sum(scored) / len(scored), 1) if scored else None

    return InterviewScorecard(
        candidate_id=evaluation.candidate_id,
        overall_score=overall,
        band=band_for(overall, threshold),
        threshold=threshold,
        questions=questions,
        competencies=competencies,
        answered_count=evaluation.evaluated_count,
        skipped_count=evaluation.skipped_count,
        review_count=evaluation.review_count,
    )


def _competency_score(
    items: list[QuestionEvaluation],
    threshold: float,
) -> CompetencyScore:
    """Aggregate one competency's questions and the concepts behind them."""

    scores = [score_question(item) for item in items]
    usable = [question.score for question in scores if question.scored]
    score = round(sum(usable) / len(usable), 1) if usable else None

    strong: list[str] = []
    weak: list[str] = []
    bonus: list[str] = []
    misconceptions: list[str] = []
    for item in items:
        for judgement in item.concept_judgements:
            target = (
                strong
                if judgement.status == ConceptJudgementStatus.DEMONSTRATED
                else weak
            )
            if judgement.concept not in target:
                target.append(judgement.concept)
        bonus.extend(
            concept for concept in item.bonus_concepts if concept not in bonus
        )
        misconceptions.extend(
            item_text
            for item_text in item.misconceptions
            if item_text not in misconceptions
        )

    return CompetencyScore(
        competency=items[0].competency,
        score=score,
        band=band_for(score, threshold),
        question_count=len(items),
        scored_count=len(usable),
        skipped_count=sum(
            item.status == QuestionEvaluationStatus.SKIPPED for item in items
        ),
        review_count=sum(
            item.status == QuestionEvaluationStatus.NEEDS_REVIEW for item in items
        ),
        demonstrated_count=sum(question.demonstrated_count for question in scores),
        partial_count=sum(question.partial_count for question in scores),
        missing_count=sum(question.missing_count for question in scores),
        strong_concepts=strong,
        missing_concepts=weak,
        bonus_concepts=bonus,
        misconceptions=misconceptions,
    )


__all__ = ["CONCEPT_WEIGHTS", "band_for", "build_scorecard", "score_question"]
