"""
Question selection for InterviewGapAI.

This module executes an InterviewPlan against Question RAG and produces
the ten concrete questions the Interview Agent asks.

It is the stage between planning and the interview session:

    ResumeAnalysis -> InterviewPlan -> [this module] -> InterviewQuestionSet

Selected retrieval configuration:
    - OpenAI text-embedding-3-small
    - Pinecone dense retrieval
    - competency + difficulty metadata filtering
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.corpus.document_builder import load_jsonl
from src.observability import traced
from src.schemas.interview_plan import CompetencyTarget, InterviewPlan
from src.schemas.interview_questions import (
    ExpectedConcepts,
    InterviewQuestionSet,
    RetrievalTrace,
    SelectedQuestion,
    UnfilledSlot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CORPUS_PATH = (
    PROJECT_ROOT
    / "data"
    / "prepared"
    / "master"
    / "interview_questions.jsonl"
)

DIFFICULTIES = (
    "basic",
    "intermediate",
    "advanced",
)

# Advanced pools are small in the current corpus: ai_security and
# python_software_engineering hold a single advanced question each. When a
# requested pool runs out, borrow from the nearest difficulty in the SAME
# competency; the competency being probed matters more than its difficulty.
DIFFICULTY_FALLBACKS = {
    "basic": ("intermediate", "advanced"),
    "intermediate": ("basic", "advanced"),
    "advanced": ("intermediate", "basic"),
}

# Ask easier questions first so a candidate is not eliminated by ordering.
DIFFICULTY_ORDER = {
    difficulty: position
    for position, difficulty in enumerate(DIFFICULTIES)
}


class QuestionSelector:
    """
    Turn an InterviewPlan into corpus-backed interview questions.

    One retrieval call is made per (competency, difficulty) bucket rather
    than per question, then the bucket's questions are taken from that
    single ranked list.
    """

    def __init__(
        self,
        corpus_path: Optional[Path] = None,
        retriever: Any = None,
        overfetch: int = 5,
        prefetch_workers: int = 8,
    ):

        self.corpus_path = Path(
            corpus_path or DEFAULT_CORPUS_PATH
        )

        # Injected retrievers keep tests offline. The real retriever is built
        # on first use so constructing a selector needs no API keys.
        self._retriever = retriever

        self.overfetch = overfetch

        # Bounded so a large plan cannot open an unbounded number of
        # sockets against OpenAI and Pinecone at once.
        self.prefetch_workers = prefetch_workers

        self._corpus: Optional[Dict[str, dict]] = None

    @property
    def retriever(self):
        """Dense retriever filtered on competency and difficulty."""

        if self._retriever is None:

            from src.retrieval.metadata_filtered_dense_retriever import (
                MetadataFilteredDenseRetriever,
            )

            self._retriever = MetadataFilteredDenseRetriever(
                k=5,
                filter_mode="competency_difficulty",
            )

        return self._retriever

    @property
    def corpus(self) -> Dict[str, dict]:
        """Master corpus records keyed by question_id."""

        if self._corpus is None:

            records = load_jsonl(self.corpus_path)

            self._corpus = {
                record["question_id"]: record
                for record in records
            }

        return self._corpus

    def select(
        self,
        plan: InterviewPlan,
    ) -> InterviewQuestionSet:
        """
        Resolve every plan slot to a corpus question.

        Returns the questions that could be filled plus an explicit record
        of any slot the corpus could not satisfy. Callers decide whether an
        incomplete set is usable; this method does not silently pad it.
        """

        # Retrieval is the slowest part of this stage and every primary
        # bucket's query is known from the plan alone, so the round trips run
        # concurrently up front. Slot filling below stays sequential because
        # used_ids deduplicates across slots, which makes the order in which
        # buckets consume questions part of the result.
        cache = self._prefetch_buckets(plan)

        used_ids: set[str] = set()
        selected: List[Tuple[str, SelectedQuestion]] = []
        unfilled: List[UnfilledSlot] = []
        warnings: List[str] = []

        for target in plan.competency_targets:

            for difficulty in DIFFICULTIES:

                count = getattr(target, difficulty)

                if count == 0:
                    continue

                questions, shortfall = self._fill_slot(
                    target=target,
                    difficulty=difficulty,
                    count=count,
                    used_ids=used_ids,
                    warnings=warnings,
                    cache=cache,
                )

                selected.extend(
                    (difficulty, question)
                    for question in questions
                )

                if shortfall:
                    unfilled.append(
                        UnfilledSlot(
                            competency=target.competency,
                            difficulty=difficulty,
                            count=shortfall,
                            reason=(
                                f"Corpus exhausted for "
                                f"{target.competency.value}: "
                                f"{shortfall} of {count} "
                                f"{difficulty} question(s) unfilled."
                            ),
                        )
                    )

        ordered = self._order_questions(selected)

        return InterviewQuestionSet(
            candidate_id=plan.candidate_id,
            questions=ordered,
            unfilled_slots=unfilled,
            warnings=warnings,
        )

    def _search(
        self,
        query: str,
        competency: str,
        difficulty: str,
        k: int,
    ) -> List[dict]:
        """One filtered retrieval call. The only network work in this stage."""

        return self.retriever.search(
            query,
            k=k,
            metadata={
                "expected_competency": competency,
                "difficulty_target": difficulty,
            },
        )

    def _prefetch_buckets(
        self,
        plan: InterviewPlan,
    ) -> Dict[Tuple[str, str, str, int], List[dict]]:
        """
        Retrieve every primary bucket concurrently, keyed for the pass below.

        A failed prefetch is not raised here. The sequential pass misses the
        cache for that bucket and calls it again inline, so a transient error
        surfaces at the point that actually needs the result rather than
        aborting the whole plan.
        """

        requests = []

        for target in plan.competency_targets:

            for difficulty in DIFFICULTIES:

                count = getattr(target, difficulty)

                if count == 0:
                    continue

                requests.append(
                    (
                        target.reason,
                        target.competency.value,
                        difficulty,
                        count + self.overfetch,
                    )
                )

        if not requests:
            return {}

        # Build the retriever before the pool starts so the lazy property is
        # not raced into existence by several workers at once.
        self.retriever

        cache: Dict[Tuple[str, str, str, int], List[dict]] = {}

        with ThreadPoolExecutor(
            max_workers=min(len(requests), self.prefetch_workers),
        ) as pool:

            futures = {
                pool.submit(self._search, *request): request
                for request in requests
            }

            for future, request in futures.items():

                try:
                    cache[request] = future.result()
                except Exception:
                    continue

        return cache

    def _fill_slot(
        self,
        target: CompetencyTarget,
        difficulty: str,
        count: int,
        used_ids: set[str],
        warnings: List[str],
        cache: Optional[Dict[Tuple[str, str, str, int], List[dict]]] = None,
    ) -> Tuple[List[SelectedQuestion], int]:
        """Take up to count unused questions for one plan slot."""

        # The plan's allocation reason is the only natural-language text the
        # plan carries. Dense retrieval needs a query; metadata filters alone
        # cannot rank a bucket.
        query = target.reason

        collected = self._take_from_pool(
            query=query,
            competency=target.competency.value,
            difficulty=difficulty,
            wanted=count,
            used_ids=used_ids,
            warnings=warnings,
            requested_difficulty=difficulty,
            filter_relaxed=False,
            target=target,
            cache=cache,
        )

        for fallback in DIFFICULTY_FALLBACKS[difficulty]:

            if len(collected) >= count:
                break

            collected.extend(
                self._take_from_pool(
                    query=query,
                    competency=target.competency.value,
                    difficulty=fallback,
                    wanted=count - len(collected),
                    used_ids=used_ids,
                    warnings=warnings,
                    requested_difficulty=difficulty,
                    filter_relaxed=True,
                    target=target,
                    cache=cache,
                )
            )

        return collected, count - len(collected)

    def _take_from_pool(
        self,
        query: str,
        competency: str,
        difficulty: str,
        wanted: int,
        used_ids: set[str],
        warnings: List[str],
        requested_difficulty: str,
        filter_relaxed: bool,
        target: CompetencyTarget,
        cache: Optional[Dict[Tuple[str, str, str, int], List[dict]]] = None,
    ) -> List[SelectedQuestion]:
        """Retrieve one bucket and convert its unused hits into questions."""

        if wanted <= 0:
            return []

        # Over-fetch so questions already used by an earlier slot can be
        # skipped without a second retrieval call.
        k = wanted + self.overfetch

        # A prefetched bucket is consumed once. Fallback buckets miss the
        # cache by design: their k depends on how many questions earlier
        # slots took, so they cannot be predicted before the pass runs.
        results = None
        if cache is not None:
            results = cache.pop((query, competency, difficulty, k), None)

        if results is None:
            results = self._search(query, competency, difficulty, k)

        collected: List[SelectedQuestion] = []

        for result in results:

            if len(collected) >= wanted:
                break

            question_id = result["question_id"]

            if question_id in used_ids:
                continue

            record = self.corpus.get(question_id)

            # A retrieved id missing from the corpus means the index and the
            # corpus have drifted. Skip it rather than ask a question whose
            # grading concepts are unknown.
            if record is None:
                warning = (
                    f"{question_id} was retrieved but is absent from "
                    f"{self.corpus_path.name}; skipped."
                )
                # The same stale id can surface in several buckets; report
                # the drift once rather than once per retrieval call.
                if warning not in warnings:
                    warnings.append(warning)
                continue

            used_ids.add(question_id)

            collected.append(
                self._build_question(
                    record=record,
                    result=result,
                    target=target,
                    query=query,
                    requested_difficulty=requested_difficulty,
                    filter_relaxed=filter_relaxed,
                )
            )

        return collected

    def _build_question(
        self,
        record: dict,
        result: dict,
        target: CompetencyTarget,
        query: str,
        requested_difficulty: str,
        filter_relaxed: bool,
    ) -> SelectedQuestion:
        """Join a retrieval hit with its curated corpus record."""

        expected = record.get("expected_concepts", {}) or {}

        return SelectedQuestion(
            # Ordering is applied once the whole set is known.
            position=1,
            question_id=record["question_id"],
            competency=target.competency,
            sub_competency=record.get("sub_competency"),
            difficulty=record["difficulty"],
            question_type=record.get("question_type"),
            # Corpus text is the candidate-facing wording. The retriever's
            # question field is parsed out of the search document.
            question=record["question"],
            expected_concepts=ExpectedConcepts(
                must_have=expected.get("must_have", []),
                bonus=expected.get("bonus", []),
            ),
            evaluation_refs=record.get("evaluation_refs", []),
            plan_reason=target.reason,
            retrieval=RetrievalTrace(
                query=query,
                score=result["score"],
                rank=result["rank"],
                requested_difficulty=requested_difficulty,
                filter_relaxed=filter_relaxed,
            ),
        )

    @staticmethod
    def _order_questions(
        selected: List[Tuple[str, SelectedQuestion]],
    ) -> List[SelectedQuestion]:
        """Order the interview basic-first, then assign asking positions."""

        # Sorting on the requested difficulty keeps a fallback question in the
        # slot the plan intended, so the ramp reflects the plan.
        ordered = sorted(
            selected,
            key=lambda item: DIFFICULTY_ORDER.get(item[0], len(DIFFICULTIES)),
        )

        questions = []

        for position, (_, question) in enumerate(ordered, start=1):

            questions.append(
                question.model_copy(
                    update={"position": position}
                )
            )

        return questions


_default_selector = None


def get_question_selector() -> QuestionSelector:
    """
    Return a reusable QuestionSelector instance.

    Avoid repeatedly creating OpenAI/Pinecone clients and reloading the
    master corpus.
    """

    global _default_selector

    if _default_selector is None:
        _default_selector = QuestionSelector()

    return _default_selector


@traced("interview.select_questions")
def select_interview_questions(
    plan: InterviewPlan,
) -> InterviewQuestionSet:
    """
    Convenience function for Interview Agent integration.
    """

    return get_question_selector().select(plan)
