"""UI-only adapter over the contributor repository's existing intake pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ui.resume_upload import ExtractedResume


class IntakeIntegrationError(RuntimeError):
    """Candidate-safe failure raised at one existing backend boundary."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True, slots=True)
class CandidateIntake:
    """Existing pipeline outputs needed by the candidate-facing UI."""

    upload: ExtractedResume
    resume: Any
    analysis: Any
    plan: Any
    question_set: Any


def build_candidate_intake(
    upload: ExtractedResume,
    *,
    resume_extractor: Callable[[str, str], Any] | None = None,
    resume_analyzer: Callable[[Any], Any] | None = None,
    interview_planner: Callable[[Any], Any] | None = None,
    question_selector: Callable[[Any], Any] | None = None,
) -> CandidateIntake:
    """Run the existing four-stage intake pipeline without changing its code."""

    if resume_extractor is None:
        from src.resume.extractor import extract_resume as resume_extractor
    if resume_analyzer is None:
        from src.resume.analyzer import analyze_resume as resume_analyzer
    if interview_planner is None:
        from src.planning.interview_planner import (
            create_interview_plan as interview_planner,
        )
    if question_selector is None:
        from src.interview.question_selector import (
            select_interview_questions as question_selector,
        )

    resume = _run_stage(
        "resume extraction",
        lambda: resume_extractor(upload.text, upload.candidate_id),
    )
    analysis = _run_stage("resume analysis", lambda: resume_analyzer(resume))
    plan = _run_stage("interview planning", lambda: interview_planner(analysis))
    question_set = _run_stage("question selection", lambda: question_selector(plan))

    if not question_set.is_complete:
        raise IntakeIntegrationError(
            "question selection",
            "The current corpus could not fill every interview-plan slot. "
            "No partial interview was started.",
        )

    return CandidateIntake(
        upload=upload,
        resume=resume,
        analysis=analysis,
        plan=plan,
        question_set=question_set,
    )


def _run_stage(stage: str, operation: Callable[[], Any]) -> Any:
    """Convert backend exceptions into a stable UI-facing integration error."""

    try:
        return operation()
    except IntakeIntegrationError:
        raise
    except Exception as error:
        raise IntakeIntegrationError(
            stage,
            f"The {stage} stage could not complete. Check runtime configuration "
            "and try again.",
        ) from error


__all__ = ["CandidateIntake", "IntakeIntegrationError", "build_candidate_intake"]
