"""Offline tests for deterministic scoring over Evaluation Agent output."""

import pytest

from src.schemas.answer_evaluation import (
    ConceptJudgement,
    ConceptJudgementStatus,
    InterviewEvaluation,
    QuestionEvaluation,
    QuestionEvaluationStatus,
    ReviewReason,
)
from src.schemas.resume_analysis import Competency
from src.schemas.scorecard import ScoreBand
from src.scoring.scorecard import build_scorecard, score_question


def _judgement(
    concept: str,
    status: ConceptJudgementStatus,
) -> ConceptJudgement:
    return ConceptJudgement(
        concept=concept,
        status=status,
        rationale="Grounded in the retrieved rubric.",
        answer_excerpt="an excerpt" if status != ConceptJudgementStatus.MISSING else None,
        evidence_ids=["EVAL-RAG-001"],
    )


def _evaluated(
    question_id: str,
    statuses: list[ConceptJudgementStatus],
    *,
    competency: Competency = Competency.RAG,
    bonus: list[str] | None = None,
    misconceptions: list[str] | None = None,
) -> QuestionEvaluation:
    return QuestionEvaluation(
        question_id=question_id,
        competency=competency,
        status=QuestionEvaluationStatus.EVALUATED,
        concept_judgements=[
            _judgement(f"concept {index}", status)
            for index, status in enumerate(statuses, start=1)
        ],
        bonus_concepts=bonus or [],
        misconceptions=misconceptions or [],
        confidence=0.8,
    )


def _terminal(
    question_id: str,
    status: QuestionEvaluationStatus,
    *,
    competency: Competency = Competency.RAG,
) -> QuestionEvaluation:
    return QuestionEvaluation(
        question_id=question_id,
        competency=competency,
        status=status,
        review_reason=(
            ReviewReason.TECHNICAL_FAILURE
            if status == QuestionEvaluationStatus.NEEDS_REVIEW
            else None
        ),
    )


class TestQuestionScore:
    def test_demonstrated_concepts_score_full_marks(self):
        score = score_question(
            _evaluated("Q1", [ConceptJudgementStatus.DEMONSTRATED] * 3)
        )

        assert score.score == 100.0
        assert score.scored is True
        assert score.demonstrated_count == 3

    def test_partial_concepts_count_half(self):
        score = score_question(
            _evaluated(
                "Q1",
                [
                    ConceptJudgementStatus.DEMONSTRATED,
                    ConceptJudgementStatus.PARTIAL,
                    ConceptJudgementStatus.MISSING,
                    ConceptJudgementStatus.MISSING,
                ],
            )
        )

        assert score.score == pytest.approx(37.5)
        assert (score.partial_count, score.missing_count) == (1, 2)

    def test_skipped_answer_scores_zero_and_still_counts(self):
        score = score_question(
            _terminal("Q1", QuestionEvaluationStatus.SKIPPED)
        )

        assert score.score == 0.0
        assert score.scored is True

    def test_needs_review_is_excluded_rather_than_zeroed(self):
        score = score_question(
            _terminal("Q1", QuestionEvaluationStatus.NEEDS_REVIEW)
        )

        assert score.scored is False
        assert score.score is None


class TestScorecard:
    def test_overall_averages_questions_not_competencies(self):
        # RAG carries two questions and security one. Averaging competencies
        # would give the single security question the same weight as both RAG
        # questions together.
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _evaluated("Q1", [ConceptJudgementStatus.DEMONSTRATED]),
                _evaluated("Q2", [ConceptJudgementStatus.DEMONSTRATED]),
                _evaluated(
                    "Q3",
                    [ConceptJudgementStatus.MISSING],
                    competency=Competency.AI_SECURITY,
                ),
            ],
        )

        scorecard = build_scorecard(evaluation)

        assert scorecard.overall_score == pytest.approx(66.7)

    def test_review_questions_leave_the_denominator(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _evaluated("Q1", [ConceptJudgementStatus.DEMONSTRATED]),
                _terminal("Q2", QuestionEvaluationStatus.NEEDS_REVIEW),
            ],
        )

        scorecard = build_scorecard(evaluation)

        assert scorecard.overall_score == 100.0
        assert scorecard.scored_count == 1
        assert scorecard.review_count == 1

    def test_skipped_questions_stay_in_the_denominator(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _evaluated("Q1", [ConceptJudgementStatus.DEMONSTRATED]),
                _terminal("Q2", QuestionEvaluationStatus.SKIPPED),
            ],
        )

        scorecard = build_scorecard(evaluation)

        assert scorecard.overall_score == 50.0
        assert scorecard.skipped_count == 1

    def test_competency_with_only_review_questions_is_not_scored(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _evaluated("Q1", [ConceptJudgementStatus.DEMONSTRATED]),
                _terminal(
                    "Q2",
                    QuestionEvaluationStatus.NEEDS_REVIEW,
                    competency=Competency.AI_SECURITY,
                ),
            ],
        )

        scorecard = build_scorecard(evaluation)
        security = next(
            item
            for item in scorecard.competencies
            if item.competency == Competency.AI_SECURITY
        )

        assert security.score is None
        assert security.band == ScoreBand.NOT_SCORED
        # An unscored competency is neither a strength nor a gap.
        assert security not in scorecard.strengths
        assert security not in scorecard.gaps

    def test_strengths_and_gaps_split_on_the_threshold(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _evaluated(
                    "Q1",
                    [ConceptJudgementStatus.DEMONSTRATED] * 4,
                    bonus=["reranking"],
                ),
                _evaluated(
                    "Q2",
                    [ConceptJudgementStatus.MISSING] * 4,
                    competency=Competency.AI_SECURITY,
                    misconceptions=["Thinks prompt injection is input validation."],
                ),
            ],
        )

        scorecard = build_scorecard(evaluation)

        assert [item.competency for item in scorecard.strengths] == [Competency.RAG]
        assert [item.competency for item in scorecard.gaps] == [Competency.AI_SECURITY]
        assert scorecard.strengths[0].bonus_concepts == ["reranking"]
        assert scorecard.gaps[0].misconceptions

    def test_ranked_competencies_put_the_weakest_first(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _evaluated("Q1", [ConceptJudgementStatus.DEMONSTRATED]),
                _evaluated(
                    "Q2",
                    [ConceptJudgementStatus.MISSING],
                    competency=Competency.AI_SECURITY,
                ),
                _terminal(
                    "Q3",
                    QuestionEvaluationStatus.NEEDS_REVIEW,
                    competency=Competency.AGENTIC_AI,
                ),
            ],
        )

        ranked = build_scorecard(evaluation).ranked_competencies

        assert [item.competency for item in ranked] == [
            Competency.AI_SECURITY,
            Competency.RAG,
            Competency.AGENTIC_AI,
        ]

    def test_concepts_are_collected_without_duplicates(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _evaluated("Q1", [ConceptJudgementStatus.DEMONSTRATED]),
                _evaluated("Q2", [ConceptJudgementStatus.DEMONSTRATED]),
            ],
        )

        scorecard = build_scorecard(evaluation)

        assert scorecard.competencies[0].strong_concepts == ["concept 1"]

    def test_fully_unscorable_interview_reports_no_overall(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[_terminal("Q1", QuestionEvaluationStatus.NEEDS_REVIEW)],
        )

        scorecard = build_scorecard(evaluation)

        assert scorecard.overall_score is None
        assert scorecard.band == ScoreBand.NOT_SCORED
