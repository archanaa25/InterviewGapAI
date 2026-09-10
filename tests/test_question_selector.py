import json
import unittest
from pathlib import Path

from src.corpus.document_builder import load_jsonl
from src.interview.question_selector import (
    DEFAULT_CORPUS_PATH,
    QuestionSelector,
)
from src.schemas.interview_plan import InterviewPlan


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    PROJECT_ROOT
    / "data"
    / "prepared"
    / "interview_plans"
    / "candidate_01_plan.json"
)


class FakeRetriever:
    """Offline stand-in that applies the same metadata filters Pinecone does."""

    def __init__(self, records):
        self.records = records
        self.calls = []

    def search(self, query, k=None, metadata=None):
        self.calls.append((query, k, metadata))

        matches = [
            record
            for record in self.records
            if record["competency"] == metadata["expected_competency"]
            and record["difficulty"] == metadata["difficulty_target"]
        ]

        return [
            {
                "question_id": record["question_id"],
                "rank": rank,
                "score": 1.0 - (rank * 0.01),
                "question": record["question"],
                "competency": record["competency"],
                "sub_competency": record["sub_competency"],
                "difficulty": record["difficulty"],
                "question_type": record["question_type"],
            }
            for rank, record in enumerate(matches[:k], start=1)
        ]


def build_record(question_id, competency, difficulty):
    return {
        "question_id": question_id,
        "role": "ai_engineer",
        "competency": competency,
        "sub_competency": f"{competency}_fundamentals",
        "difficulty": difficulty,
        "question_type": "conceptual",
        "question": f"Question {question_id}?",
        "expected_concepts": {"must_have": ["concept a"], "bonus": []},
        "evaluation_refs": [f"EVAL-{competency.upper()}"],
        "tags": [competency],
    }


def build_plan(competency, basic, intermediate, advanced):
    return InterviewPlan.model_validate(
        {
            "candidate_id": "candidate_test",
            "total_questions": 10,
            "competency_targets": [
                {
                    "competency": competency,
                    "basic": basic,
                    "intermediate": intermediate,
                    "advanced": advanced,
                    "reason": "Probe this competency.",
                }
            ],
            "difficulty_distribution": {
                "basic": basic,
                "intermediate": intermediate,
                "advanced": advanced,
            },
            "strategy": {"rationale": "Test strategy."},
        }
    )


class QuestionSelectorRealCorpusTests(unittest.TestCase):
    """Run a real interview plan against the real master corpus, offline."""

    @classmethod
    def setUpClass(cls):
        cls.records = load_jsonl(DEFAULT_CORPUS_PATH)
        cls.plan = InterviewPlan.model_validate(
            json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        )

    def setUp(self):
        self.retriever = FakeRetriever(self.records)
        self.selector = QuestionSelector(retriever=self.retriever)

    def test_plan_resolves_to_ten_unique_questions(self):
        result = self.selector.select(self.plan)

        self.assertTrue(result.is_complete, result.unfilled_slots)
        self.assertEqual(len(result.questions), 10)
        self.assertEqual(
            len({question.question_id for question in result.questions}), 10
        )
        self.assertEqual(
            [question.position for question in result.questions],
            list(range(1, 11)),
        )
        self.assertEqual(result.warnings, [])

    def test_every_question_carries_grading_concepts(self):
        result = self.selector.select(self.plan)

        for question in result.questions:
            self.assertTrue(
                question.expected_concepts.must_have,
                f"{question.question_id} has no must-have concepts",
            )
            self.assertTrue(question.evaluation_refs)
            self.assertTrue(question.question)

    def test_selection_honours_planned_competency_allocation(self):
        result = self.selector.select(self.plan)

        for target in self.plan.competency_targets:
            selected = [
                question
                for question in result.questions
                if question.competency == target.competency
            ]
            self.assertEqual(len(selected), target.question_count)

    def test_questions_are_ordered_basic_first(self):
        result = self.selector.select(self.plan)

        order = {"basic": 0, "intermediate": 1, "advanced": 2}
        tiers = [
            order[question.retrieval.requested_difficulty]
            for question in result.questions
        ]
        self.assertEqual(tiers, sorted(tiers))

    def test_one_retrieval_call_per_populated_bucket(self):
        self.selector.select(self.plan)

        buckets = sum(
            1
            for target in self.plan.competency_targets
            for difficulty in ("basic", "intermediate", "advanced")
            if getattr(target, difficulty) > 0
        )
        self.assertEqual(len(self.retriever.calls), buckets)


class QuestionSelectorFallbackTests(unittest.TestCase):
    def test_exhausted_difficulty_falls_back_within_competency(self):
        records = [
            build_record("RAG-ADV-001", "rag", "advanced"),
            build_record("RAG-INT-001", "rag", "intermediate"),
            build_record("RAG-INT-002", "rag", "intermediate"),
        ]
        selector = QuestionSelector(retriever=FakeRetriever(records))
        selector._corpus = {record["question_id"]: record for record in records}

        result = selector.select(build_plan("rag", 0, 0, 10))

        self.assertEqual(len(result.questions), 3)
        relaxed = [q for q in result.questions if q.retrieval.filter_relaxed]
        self.assertEqual(len(relaxed), 2)
        for question in relaxed:
            self.assertEqual(question.difficulty, "intermediate")
            self.assertEqual(question.retrieval.requested_difficulty, "advanced")

    def test_unfillable_slot_is_reported_not_padded(self):
        records = [build_record("RAG-ADV-001", "rag", "advanced")]
        selector = QuestionSelector(retriever=FakeRetriever(records))
        selector._corpus = {record["question_id"]: record for record in records}

        result = selector.select(build_plan("rag", 0, 0, 10))

        self.assertFalse(result.is_complete)
        self.assertEqual(len(result.unfilled_slots), 1)
        self.assertEqual(result.unfilled_slots[0].count, 9)
        self.assertEqual(result.unfilled_slots[0].difficulty, "advanced")

    def test_question_missing_from_corpus_is_skipped_with_warning(self):
        records = [
            build_record("RAG-BAS-001", "rag", "basic"),
            build_record("RAG-BAS-002", "rag", "basic"),
        ]
        selector = QuestionSelector(retriever=FakeRetriever(records))
        # The index still serves a question the corpus no longer contains.
        selector._corpus = {"RAG-BAS-002": records[1]}

        result = selector.select(build_plan("rag", 1, 0, 9))

        self.assertEqual(len(result.questions), 1)
        self.assertEqual(result.questions[0].question_id, "RAG-BAS-002")
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("RAG-BAS-001", result.warnings[0])


if __name__ == "__main__":
    unittest.main()
