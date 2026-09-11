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


def build_record(
    question_id,
    competency,
    difficulty,
    sub_competency=None,
    must_have=("concept a",),
):
    return {
        "question_id": question_id,
        "role": "ai_engineer",
        "competency": competency,
        "sub_competency": sub_competency or f"{competency}_fundamentals",
        "difficulty": difficulty,
        "question_type": "conceptual",
        "question": f"Question {question_id}?",
        "expected_concepts": {"must_have": list(must_have), "bonus": []},
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


class QuestionSelectorPrefetchTests(unittest.TestCase):
    """Concurrent prefetch must not change what the sequential pass produces."""

    @classmethod
    def setUpClass(cls):
        cls.records = load_jsonl(DEFAULT_CORPUS_PATH)
        cls.plan = InterviewPlan.model_validate(
            json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        )

    def _select(self, prefetch):
        selector = QuestionSelector(retriever=FakeRetriever(self.records))

        if not prefetch:
            selector._prefetch_buckets = lambda plan: {}

        return selector.select(self.plan)

    def test_prefetched_selection_matches_sequential_selection(self):
        serial = self._select(prefetch=False)
        parallel = self._select(prefetch=True)

        self.assertEqual(
            [question.question_id for question in serial.questions],
            [question.question_id for question in parallel.questions],
        )
        self.assertEqual(
            serial.model_dump_json(),
            parallel.model_dump_json(),
        )

    def test_bucket_is_retrieved_once_when_prefetched(self):
        retriever = FakeRetriever(self.records)
        selector = QuestionSelector(retriever=retriever)

        selector.select(self.plan)

        # A cached bucket must be consumed, not re-fetched by the pass that
        # follows it. Duplicate (competency, difficulty) calls would mean the
        # cache key and the call site have drifted apart.
        keys = [
            (metadata["expected_competency"], metadata["difficulty_target"])
            for _, _, metadata in retriever.calls
        ]
        self.assertEqual(len(keys), len(set(keys)))

    def test_failed_prefetch_falls_back_to_an_inline_call(self):
        selector = QuestionSelector(retriever=FakeRetriever(self.records))

        # A prefetch that returns nothing stands in for one that raised: the
        # sequential pass must still fill every slot on its own.
        selector._prefetch_buckets = lambda plan: {}

        result = selector.select(self.plan)

        self.assertTrue(result.is_complete, result.unfilled_slots)
        self.assertEqual(len(result.questions), 10)


def build_filler(competency, count, difficulty="advanced"):
    """Distinct-topic records so a padded slot does not consume the pool under test."""

    return [
        build_record(
            f"{competency.upper()}-FILL-{index}",
            competency,
            difficulty,
            sub_competency=f"filler_topic_{index}",
            must_have=[f"filler concept {index}"],
        )
        for index in range(count)
    ]


class QuestionSelectorRedundancyTests(unittest.TestCase):
    """Two slots in one competency should not test one topic twice."""

    @staticmethod
    def _selector(records):
        selector = QuestionSelector(retriever=FakeRetriever(records))
        selector._corpus = {record["question_id"]: record for record in records}
        return selector

    @staticmethod
    def _by_requested(result, difficulty):
        return {
            question.question_id
            for question in result.questions
            if question.retrieval.requested_difficulty == difficulty
        }

    def test_second_slot_prefers_an_unused_sub_competency(self):
        # The shape that motivated this check: two questions in one
        # sub_competency, sharing no must-have concept wording, that are
        # nonetheless two probes of the same narrow topic.
        records = [
            build_record(
                "AGENT-FUND-BAS-001", "agentic_ai", "basic",
                sub_competency="agent_fundamentals",
                must_have=["dynamic execution path"],
            ),
            build_record(
                "AGENT-FUND-INT-001", "agentic_ai", "intermediate",
                sub_competency="agent_fundamentals",
                must_have=["fixed paths improve auditability"],
            ),
            build_record(
                "AGENT-MEM-INT-001", "agentic_ai", "intermediate",
                sub_competency="agent_memory",
                must_have=["state persists across turns"],
            ),
        ] + build_filler("agentic_ai", 8)

        result = self._selector(records).select(
            build_plan("agentic_ai", 1, 1, 8)
        )

        self.assertTrue(result.is_complete, result.unfilled_slots)
        self.assertEqual(
            self._by_requested(result, "basic"), {"AGENT-FUND-BAS-001"}
        )
        # agent_fundamentals is already spent, so the intermediate slot takes
        # the other topic rather than the second half of the same trade-off.
        self.assertEqual(
            self._by_requested(result, "intermediate"), {"AGENT-MEM-INT-001"}
        )
        self.assertEqual(result.warnings, [])

    def test_repeated_concepts_are_caught_across_sub_competencies(self):
        records = [
            build_record(
                "RAG-A", "rag", "intermediate",
                sub_competency="rag_retrieval",
                must_have=["hybrid retrieval", "reranking"],
            ),
            build_record(
                "RAG-B", "rag", "intermediate",
                sub_competency="rag_serving",
                must_have=["hybrid retrieval", "reranking"],
            ),
            build_record(
                "RAG-C", "rag", "intermediate",
                sub_competency="rag_chunking",
                must_have=["chunk size affects recall"],
            ),
        ] + build_filler("rag", 8)

        result = self._selector(records).select(build_plan("rag", 0, 2, 8))

        self.assertEqual(
            self._by_requested(result, "intermediate"), {"RAG-A", "RAG-C"}
        )
        self.assertEqual(result.warnings, [])

    def test_a_redundant_question_beats_an_unfilled_slot(self):
        # An unfilled slot aborts the whole intake at the gateway, so when the
        # corpus offers nothing else the held-back question is admitted - and
        # the reason is recorded rather than hidden.
        # No filler here on purpose: with another topic available at any
        # difficulty the selector prefers that (variety over difficulty match),
        # so isolating the admit path means offering it nothing else.
        records = [
            build_record("RAG-INT-001", "rag", "intermediate"),
            build_record("RAG-INT-002", "rag", "intermediate"),
        ]

        result = self._selector(records).select(build_plan("rag", 0, 2, 8))

        self.assertEqual(
            self._by_requested(result, "intermediate"),
            {"RAG-INT-001", "RAG-INT-002"},
        )
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("repeats", result.warnings[0])

    def test_a_held_back_question_stays_available_to_a_later_slot(self):
        # Deferring must not consume the candidate. RAG-INT-002 is redundant
        # for the intermediate slot, but the advanced slot exhausts its own
        # pool and must still be able to fall back onto it.
        records = [
            build_record(
                "RAG-INT-001", "rag", "intermediate",
                sub_competency="rag_retrieval", must_have=["a"],
            ),
            build_record(
                "RAG-INT-002", "rag", "intermediate",
                sub_competency="rag_retrieval", must_have=["a"],
            ),
            build_record(
                "RAG-ADV-001", "rag", "advanced",
                sub_competency="rag_serving", must_have=["b"],
            ),
        ]

        result = self._selector(records).select(build_plan("rag", 0, 1, 9))

        self.assertEqual(
            {question.question_id for question in result.questions},
            {"RAG-INT-001", "RAG-ADV-001", "RAG-INT-002"},
        )


if __name__ == "__main__":
    unittest.main()
