"""UI-only adapter over the contributor repository's existing intake pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ui.resume_upload import ExtractedResume


_logger = logging.getLogger("interviewgap.ui.gateway")


class IntakeIntegrationError(RuntimeError):
    """Candidate-safe failure raised at one existing backend boundary."""

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


def build_candidate_plan(
    upload: ExtractedResume,
    *,
    resume_extractor: Callable[[str, str], Any] | None = None,
    resume_analyzer: Callable[[Any], Any] | None = None,
    interview_planner: Callable[[Any], Any] | None = None,
    on_stage: Callable[[str], None] | None = None,
    on_result: Callable[[str, Any], None] | None = None,
) -> CandidatePlan:
    """
    Run intake stages 1-3: resume text to a validated interview plan.

    on_stage fires as a stage begins, on_result as it finishes. The second
    exists so a caller can show a stage's output while the next one is still
    running, rather than holding all three back until the last returns.
    """

    if resume_extractor is None:
        from src.resume.extractor import extract_resume as resume_extractor
    if resume_analyzer is None:
        from src.resume.analyzer import analyze_resume as resume_analyzer
    if interview_planner is None:
        from src.planning.interview_planner import (
            create_interview_plan as interview_planner,
        )

    resume = _run_stage(
        "resume extraction",
        lambda: resume_extractor(upload.text, upload.candidate_id),
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
    on_stage: Callable[[str], None] | None = None,
) -> CandidateIntake:
    """Run the existing four-stage intake pipeline without changing its code."""

    prepared = build_candidate_plan(
        upload,
        resume_extractor=resume_extractor,
        resume_analyzer=resume_analyzer,
        interview_planner=interview_planner,
        on_stage=on_stage,
    )

    return resolve_interview_questions(
        prepared,
        question_selector=question_selector,
        on_stage=on_stage,
    )


def _run_stage(
    stage: str,
    operation: Callable[[], Any],
    on_stage: Callable[[str], None] | None = None,
    on_result: Callable[[str, Any], None] | None = None,
) -> Any:
    """Convert backend exceptions into a stable UI-facing integration error."""

    if on_stage is not None:
        on_stage(stage)

    try:
        value = operation()
    except IntakeIntegrationError:
        raise
    except Exception as error:
        # The candidate-facing message stays deliberately vague, but an
        # operator reading the server log needs the real cause: without it a
        # transient rate limit and a misconfigured key look identical.
        _logger.exception("intake stage %r failed", stage)
        raise IntakeIntegrationError(
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
    "IntakeIntegrationError",
    "build_candidate_intake",
    "build_candidate_plan",
    "resolve_interview_questions",
]
