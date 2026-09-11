"""Tests for the additive adapter over the existing intake stages."""

from types import SimpleNamespace

import pytest

from ui.gateway import (
    IntakeIntegrationError,
    build_candidate_intake,
    build_candidate_plan,
    prefetch_resume,
)
from ui.resume_upload import ExtractedResume, ResumeFormat


def _upload() -> ExtractedResume:
    return ExtractedResume(
        filename="candidate.md",
        format=ResumeFormat.MARKDOWN,
        media_type="text/markdown",
        size_bytes=25,
        sha256="a" * 64,
        text="# Candidate\nPython engineer",
        extraction_method="utf-8",
    )


def test_gateway_calls_existing_pipeline_contracts_in_order() -> None:
    """The UI adapter passes each existing stage output to the next stage."""

    calls: list[tuple[str, object]] = []
    resume = SimpleNamespace(name="Candidate")
    analysis = object()
    plan = object()
    questions = SimpleNamespace(is_complete=True)

    def extract(text: str, candidate_id: str):
        calls.append(("extract", (text, candidate_id)))
        return resume

    def analyze(value):
        calls.append(("analyze", value))
        return analysis

    def plan_interview(value):
        calls.append(("plan", value))
        return plan

    def select(value):
        calls.append(("questions", value))
        return questions

    result = build_candidate_intake(
        _upload(),
        resume_extractor=extract,
        resume_analyzer=analyze,
        interview_planner=plan_interview,
        question_selector=select,
    )

    assert result.resume is resume
    assert result.analysis is analysis
    assert result.plan is plan
    assert result.question_set is questions
    assert calls == [
        ("extract", ("# Candidate\nPython engineer", "upload-aaaaaaaaaaaaaaaa")),
        ("analyze", resume),
        ("plan", analysis),
        ("questions", plan),
    ]


def test_gateway_collects_a_prefetched_resume_instead_of_extracting_again() -> None:
    """Stage 1 started at upload time is collected, not repeated, on the click."""

    extractions: list[str] = []
    resume = SimpleNamespace(name="Candidate")

    def extract(text: str, candidate_id: str):
        extractions.append(candidate_id)
        return resume

    upload = _upload()
    pending = prefetch_resume(upload, resume_extractor=extract)

    prepared = build_candidate_plan(
        upload,
        resume_extractor=extract,
        resume_analyzer=lambda value: value,
        interview_planner=lambda value: value,
        prefetched_resume=pending,
    )

    assert prepared.resume is resume
    assert extractions == ["upload-aaaaaaaaaaaaaaaa"]


def test_gateway_hides_a_failed_prefetch_behind_the_stage_contract() -> None:
    """A prefetch that failed reports as its stage, not as a raw provider error."""

    def fail(_text: str, _candidate_id: str):
        raise RuntimeError("secret provider payload")

    upload = _upload()
    pending = prefetch_resume(upload, resume_extractor=fail)

    with pytest.raises(IntakeIntegrationError) as captured:
        build_candidate_plan(
            upload,
            resume_analyzer=lambda value: value,
            interview_planner=lambda value: value,
            prefetched_resume=pending,
        )

    assert captured.value.stage == "resume extraction"
    assert "secret provider payload" not in str(captured.value)


def test_gateway_refuses_a_partial_question_set() -> None:
    """The UI does not silently start an interview with unfilled plan slots."""

    with pytest.raises(IntakeIntegrationError) as captured:
        build_candidate_intake(
            _upload(),
            resume_extractor=lambda _text, _candidate_id: object(),
            resume_analyzer=lambda _resume: object(),
            interview_planner=lambda _analysis: object(),
            question_selector=lambda _plan: SimpleNamespace(is_complete=False),
        )

    assert captured.value.stage == "question selection"


def test_gateway_hides_backend_exception_details() -> None:
    """Provider internals do not leak through the candidate error contract."""

    def fail(_text: str, _candidate_id: str):
        raise RuntimeError("secret provider payload")

    with pytest.raises(IntakeIntegrationError) as captured:
        build_candidate_intake(
            _upload(),
            resume_extractor=fail,
            resume_analyzer=lambda value: value,
            interview_planner=lambda value: value,
            question_selector=lambda value: value,
        )

    assert captured.value.stage == "resume extraction"
    assert "secret provider payload" not in str(captured.value)
