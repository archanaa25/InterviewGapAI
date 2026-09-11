"""UI-only adapter over the contributor repository's existing intake pipeline."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import dataclass
from typing import Any

from src.observability import log_event
from ui.resume_upload import ExtractedResume


# Stage 1 depends only on the uploaded bytes, so it can start the moment the
# file lands instead of waiting for the candidate to press the button. One
# small pool, shared across sessions, keeps a stalled extraction from
# accumulating threads.
_prefetch_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ig-prefetch")


class IntakeIntegrationError(RuntimeError):
    """Candidate-safe failure raised at one existing backend boundary."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


class EvaluationIntegrationError(RuntimeError):
    """Candidate-safe failure raised at the answer-evaluation boundary."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True, slots=True)
class CandidatePlan:
    """
    Everything the plan screen needs, without the questions.

    Stages 1-3 answer "what will this interview cover and why", which is all
    the candidate is shown before starting. Question selection is a separate
    phase so that its latency lands while the plan is on screen rather than
    in front of it.
    """

    upload: ExtractedResume
    resume: Any
    analysis: Any
    plan: Any


@dataclass(frozen=True, slots=True)
class CandidateIntake:
    """Existing pipeline outputs needed by the candidate-facing UI."""

    upload: ExtractedResume
    resume: Any
    analysis: Any
    plan: Any
    question_set: Any


def prefetch_resume(
    upload: ExtractedResume,
    *,
    resume_extractor: Callable[[str, str], Any] | None = None,
) -> Future:
    """
    Start stage 1 in the background and return its pending result.

    Pass the future to build_candidate_plan to collect it. A future that is
    never collected is harmless: it completes and is discarded.
    """

    if resume_extractor is None:
        from src.resume.extractor import extract_resume as resume_extractor

    # Copy the caller's context so the extraction span nests under whatever
    # request context the caller established, rather than starting its own.
    return _prefetch_pool.submit(
        copy_context().run,
        resume_extractor,
        upload.text,
        upload.candidate_id,
    )


def build_candidate_plan(
    upload: ExtractedResume,
    *,
    resume_extractor: Callable[[str, str], Any] | None = None,
    resume_analyzer: Callable[[Any], Any] | None = None,
    interview_planner: Callable[[Any], Any] | None = None,
    prefetched_resume: Future | None = None,
    on_stage: Callable[[str], None] | None = None,
    on_result: Callable[[str, Any], None] | None = None,
) -> CandidatePlan:
    """
    Run intake stages 1-3: resume text to a validated interview plan.

    on_stage fires as a stage begins, on_result as it finishes. The second
    exists so a caller can show a stage's output while the next one is still
    running, rather than holding all three back until the last returns.

    prefetched_resume collects a stage 1 run already started by
    prefetch_resume, including its failure. Stage 1 is otherwise run here.
    """

    if resume_extractor is None:
        from src.resume.extractor import extract_resume as resume_extractor
    if resume_analyzer is None:
        from src.resume.analyzer import analyze_resume as resume_analyzer
    if interview_planner is None:
        from src.planning.interview_planner import (
            create_interview_plan as interview_planner,
        )

    def extract() -> Any:
        if prefetched_resume is not None:
            return prefetched_resume.result()
        return resume_extractor(upload.text, upload.candidate_id)

    resume = _run_stage(
        "resume extraction",
        extract,
        on_stage,
        on_result,
    )
    analysis = _run_stage(
        "resume analysis",
        lambda: resume_analyzer(resume),
        on_stage,
        on_result,
    )
    plan = _run_stage(
        "interview planning",
        lambda: interview_planner(analysis),
        on_stage,
        on_result,
    )

    return CandidatePlan(
        upload=upload,
        resume=resume,
        analysis=analysis,
        plan=plan,
    )


def resolve_interview_questions(
    prepared: CandidatePlan,
    *,
    question_selector: Callable[[Any], Any] | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> CandidateIntake:
    """Run intake stage 4: resolve the plan's slots to corpus questions."""

    if question_selector is None:
        from src.interview.question_selector import (
            select_interview_questions as question_selector,
        )

    question_set = _run_stage(
        "question selection",
        lambda: question_selector(prepared.plan),
        on_stage,
    )

    if not question_set.is_complete:
        raise IntakeIntegrationError(
            "question selection",
            "The current corpus could not fill every interview-plan slot. "
            "No partial interview was started.",
        )

    return CandidateIntake(
        upload=prepared.upload,
        resume=prepared.resume,
        analysis=prepared.analysis,
        plan=prepared.plan,
        question_set=question_set,
    )


def build_candidate_intake(
    upload: ExtractedResume,
    *,
    resume_extractor: Callable[[str, str], Any] | None = None,
    resume_analyzer: Callable[[Any], Any] | None = None,
    interview_planner: Callable[[Any], Any] | None = None,
    question_selector: Callable[[Any], Any] | None = None,
    prefetched_resume: Future | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> CandidateIntake:
    """Run the existing four-stage intake pipeline without changing its code."""

    prepared = build_candidate_plan(
        upload,
        resume_extractor=resume_extractor,
        resume_analyzer=resume_analyzer,
        interview_planner=interview_planner,
        prefetched_resume=prefetched_resume,
        on_stage=on_stage,
    )

    return resolve_interview_questions(
        prepared,
        question_selector=question_selector,
        on_stage=on_stage,
    )


def evaluate_candidate_interview(
    intake: CandidateIntake,
    progress: Any,
    *,
    evaluator: Callable[[Any, dict[str, str]], Any] | None = None,
    on_stage: Callable[[str], None] | None = None,
) -> Any:
    """Hand one complete answer set to the backend Evaluation Agent."""

    if evaluator is None:
        from src.evaluation.agent import evaluate_interview_answers as evaluator

    if not getattr(progress, "submitted", False):
        raise EvaluationIntegrationError(
            "answer evaluation",
            "The interview must be submitted before evaluation begins.",
        )

    answers = {
        answer.question_id: answer.text
        for answer in progress.answers
    }

    return _run_stage(
        "answer evaluation",
        lambda: evaluator(intake.question_set, answers),
        on_stage,
        error_class=EvaluationIntegrationError,
    )


def _run_stage(
    stage: str,
    operation: Callable[[], Any],
    on_stage: Callable[[str], None] | None = None,
    on_result: Callable[[str, Any], None] | None = None,
    error_class: type[RuntimeError] = IntakeIntegrationError,
) -> Any:
    """Convert backend exceptions into a stable UI-facing integration error."""

    if on_stage is not None:
        on_stage(stage)

    try:
        value = operation()
    except (IntakeIntegrationError, EvaluationIntegrationError):
        raise
    except Exception as error:
        # The candidate-facing message stays deliberately vague, but an
        # operator reading the server log needs the real cause: without it a
        # transient rate limit and a misconfigured key look identical.
        # log_event records the exception type only, per this project's
        # telemetry contract - never the exception message or traceback,
        # which can carry a provider response (a billing URL, an account
        # detail) that has no business in a log line.
        log_event(
            "intake.stage_failed",
            level="ERROR",
            stage=stage,
            error_type=type(error).__name__,
        )
        raise error_class(
            stage,
            f"The {stage} stage could not complete. Check runtime configuration "
            "and try again.",
        ) from error

    if on_result is not None:
        on_result(stage, value)

    return value


__all__ = [
    "CandidateIntake",
    "CandidatePlan",
    "EvaluationIntegrationError",
    "IntakeIntegrationError",
    "build_candidate_intake",
    "build_candidate_plan",
    "evaluate_candidate_interview",
    "prefetch_resume",
    "resolve_interview_questions",
]
