"""Offline tests for matching curated resources to competency scores."""

import json

import pytest

from src.learning.recommendations import build_learning_plan, load_catalog
from src.schemas.answer_evaluation import (
    ConceptJudgement,
    ConceptJudgementStatus,
    InterviewEvaluation,
    QuestionEvaluation,
    QuestionEvaluationStatus,
    ReviewReason,
)
from src.schemas.learning import LearningCatalog
from src.schemas.resume_analysis import Competency
from src.scoring.scorecard import build_scorecard


def _catalog() -> LearningCatalog:
    return LearningCatalog.model_validate(
        {
            "version": "test",
            "recommendation_config": {
                "competency_threshold": 70,
                "max_resources_per_competency": 2,
            },
            "competencies": {
                "rag": {
                    "display_name": "RAG",
                    "resources": [
                        {
                            "resource_id": "RAG-003",
                            "title": "Third",
                            "provider": "Substack",
                            "type": "article",
                            "url": "https://example.com/three",
                            "priority": 3,
                        },
                        {
                            "resource_id": "RAG-001",
                            "title": "First",
                            "provider": "Maven",
                            "type": "course",
                            "url": "https://example.com/one",
                            "priority": 1,
                        },
                        {
                            "resource_id": "RAG-002",
                            "title": "Second",
                            "provider": "DeepLearning.AI",
                            "type": "course",
                            "url": "https://example.com/two",
                            "priority": 2,
                        },
                    ],
                },
                "ai_security": {
                    "display_name": "AI Security",
                    "resources": [
                        {
                            "resource_id": "SEC-001",
                            "title": "Security first",
                            "provider": "OWASP",
                            "type": "guide",
                            "url": "https://example.com/sec",
                            "priority": 1,
                        }
                    ],
                },
            },
        }
    )


def _question(
    question_id: str,
    competency: Competency,
    statuses: list[ConceptJudgementStatus],
) -> QuestionEvaluation:
    return QuestionEvaluation(
        question_id=question_id,
        competency=competency,
        status=QuestionEvaluationStatus.EVALUATED,
        concept_judgements=[
            ConceptJudgement(
                concept=f"{competency.value} concept {index}",
                status=status,
                rationale="Grounded.",
                answer_excerpt=(
                    "excerpt" if status != ConceptJudgementStatus.MISSING else None
                ),
                evidence_ids=["EVAL-001"],
            )
            for index, status in enumerate(statuses, start=1)
        ],
        confidence=0.7,
    )


def _plan(rag: list[ConceptJudgementStatus], security: list[ConceptJudgementStatus]):
    evaluation = InterviewEvaluation(
        candidate_id="cand-1",
        questions=[
            _question("Q1", Competency.RAG, rag),
            _question("Q2", Competency.AI_SECURITY, security),
        ],
    )
    return build_learning_plan(build_scorecard(evaluation), catalog=_catalog())


class TestLearningPlan:
    def test_every_competency_appears_weakest_first(self):
        plan = _plan(
            [ConceptJudgementStatus.DEMONSTRATED] * 4,
            [ConceptJudgementStatus.MISSING] * 4,
        )

        assert [item.competency for item in plan.recommendations] == [
            Competency.AI_SECURITY,
            Competency.RAG,
        ]

    def test_below_threshold_competencies_are_flagged_priority(self):
        plan = _plan(
            [ConceptJudgementStatus.DEMONSTRATED] * 4,
            [ConceptJudgementStatus.MISSING] * 4,
        )

        flags = {item.competency: item.is_priority for item in plan.recommendations}
        assert flags == {Competency.AI_SECURITY: True, Competency.RAG: False}
        assert plan.priority_count == 1

    def test_a_strong_candidate_still_receives_resources(self):
        plan = _plan(
            [ConceptJudgementStatus.DEMONSTRATED] * 4,
            [ConceptJudgementStatus.DEMONSTRATED] * 4,
        )

        assert plan.priority_count == 0
        assert len(plan.recommendations) == 2
        assert all(item.resources for item in plan.recommendations)

    def test_resources_follow_catalog_priority_within_the_limit(self):
        plan = _plan(
            [ConceptJudgementStatus.MISSING] * 4,
            [ConceptJudgementStatus.DEMONSTRATED] * 4,
        )
        rag = next(
            item for item in plan.recommendations if item.competency == Competency.RAG
        )

        assert [resource.resource_id for resource in rag.resources] == [
            "RAG-001",
            "RAG-002",
        ]

    def test_focus_concepts_come_from_what_the_answers_missed(self):
        plan = _plan(
            [ConceptJudgementStatus.DEMONSTRATED] * 4,
            [
                ConceptJudgementStatus.MISSING,
                ConceptJudgementStatus.PARTIAL,
                ConceptJudgementStatus.DEMONSTRATED,
                ConceptJudgementStatus.MISSING,
            ],
        )
        security = next(
            item
            for item in plan.recommendations
            if item.competency == Competency.AI_SECURITY
        )

        assert "ai_security concept 3" not in security.focus_concepts
        assert len(security.focus_concepts) == 3

    def test_a_competency_missing_from_the_catalog_is_omitted(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                _question(
                    "Q1",
                    Competency.AGENTIC_AI,
                    [ConceptJudgementStatus.MISSING],
                )
            ],
        )

        plan = build_learning_plan(build_scorecard(evaluation), catalog=_catalog())

        assert plan.recommendations == []

    def test_an_unscored_competency_is_not_called_a_gap(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                QuestionEvaluation(
                    question_id="Q1",
                    competency=Competency.RAG,
                    status=QuestionEvaluationStatus.NEEDS_REVIEW,
                    review_reason=ReviewReason.TECHNICAL_FAILURE,
                )
            ],
        )

        plan = build_learning_plan(build_scorecard(evaluation), catalog=_catalog())

        assert plan.recommendations[0].is_priority is False
        assert "unassessed" in plan.recommendations[0].reason


class TestShippedCatalog:
    def test_catalog_covers_every_competency_the_interview_can_assess(self):
        catalog = load_catalog()

        assert set(catalog.competencies) == set(Competency)

    def test_catalog_resources_are_uniquely_identified(self):
        catalog = load_catalog()
        ids = [
            resource.resource_id
            for entry in catalog.competencies.values()
            for resource in entry.resources
        ]

        assert len(ids) == len(set(ids))

    def test_missing_catalog_file_raises_a_named_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_catalog(str(tmp_path / "absent.json"))


class TestSkippedCompetency:
    def test_a_fully_skipped_competency_is_not_told_its_answers_were_wrong(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                QuestionEvaluation(
                    question_id="Q1",
                    competency=Competency.RAG,
                    status=QuestionEvaluationStatus.SKIPPED,
                )
            ],
        )

        plan = build_learning_plan(build_scorecard(evaluation), catalog=_catalog())
        recommendation = plan.recommendations[0]

        assert recommendation.score == 0.0
        assert recommendation.is_priority is True
        assert "skipped every question" in recommendation.reason
        assert "your answers missed" not in recommendation.reason.lower()

    def test_a_partly_skipped_competency_still_reports_the_gap(self):
        evaluation = InterviewEvaluation(
            candidate_id="cand-1",
            questions=[
                QuestionEvaluation(
                    question_id="Q1",
                    competency=Competency.RAG,
                    status=QuestionEvaluationStatus.SKIPPED,
                ),
                _question("Q2", Competency.RAG, [ConceptJudgementStatus.MISSING] * 2),
            ],
        )

        plan = build_learning_plan(build_scorecard(evaluation), catalog=_catalog())

        assert "skipped every question" not in plan.recommendations[0].reason
        assert plan.recommendations[0].focus_concepts


class TestFeaturedSection:
    def test_the_shipped_catalog_carries_every_featured_link(self):
        featured = load_catalog().featured

        assert featured is not None
        urls = (
            [str(featured.highlight.url)]
            + [str(resource.url) for resource in featured.reading]
            + [str(person.url) for person in featured.people]
            + [str(featured.community.url)]
        )
        assert len(urls) == len(set(urls)), "a link is listed twice"
        assert all(url.startswith("https://") for url in urls)

    def test_the_academy_closes_the_section(self):
        """The organisation is listed after the people who teach for it."""

        featured = load_catalog().featured

        assert "the-gen-academy" in str(featured.community.url)
        assert featured.community.name == "The Gen Academy"

    def test_the_cohort_is_flagged_as_paid_with_its_standing_detail(self):
        """A candidate must not read a $2,499 cohort as another free course."""

        highlight = load_catalog().featured.highlight

        assert highlight.free is False
        assert highlight.note
        assert "2026" in highlight.note

    def test_featured_links_reach_the_plan_without_becoming_recommendations(self):
        """Standing links must never displace a score-driven resource."""

        plan = _plan(
            [ConceptJudgementStatus.MISSING] * 4,
            [ConceptJudgementStatus.MISSING] * 4,
        )
        plan_with_featured = build_learning_plan(
            build_scorecard(
                InterviewEvaluation(
                    candidate_id="cand-1",
                    questions=[
                        _question("Q1", Competency.RAG, [ConceptJudgementStatus.MISSING])
                    ],
                )
            ),
            catalog=load_catalog(),
        )

        assert plan.featured is None, "the test catalog has no featured block"
        assert plan_with_featured.featured is not None
        competencies = {
            item.competency for item in plan_with_featured.recommendations
        }
        assert competencies == {Competency.RAG}
