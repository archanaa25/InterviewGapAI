import os
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.schemas.resume import CandidateResume
from src.schemas.resume_analysis import (
    Competency,
    CompetencyEvidence,
    ResumeAnalysis,
)
from src.resume.analyzer_prompts import (
    COMPETENCY_EVIDENCE_SYSTEM_PROMPT,
    RESUME_SUMMARY_SYSTEM_PROMPT,
)
from src.observability import traced, trace_span
from src.llm_client import build_client
from src.llm_retry import call_with_retry


load_dotenv()

# Eight concurrent requests are eight chances to meet a transient overload,
# and any one of them failing fails the whole stage for the candidate. The
# extra retries buy back the reliability the fan-out spends - but only for
# failures a retry can fix; call_with_retry owns that decision.
# LLM_PROVIDER=deepseek switches the client and this default together; an
# explicit RESUME_ANALYSIS_MODEL still wins over either provider's default.
client, _default_model = build_client("gpt-5.6")
ANALYSIS_MODEL = os.getenv("RESUME_ANALYSIS_MODEL", _default_model)
ANALYSIS_MAX_RETRIES = 4

COMPETENCIES = tuple(Competency)


class _ResumeSummary(BaseModel):
    """The one part of ResumeAnalysis that spans every competency."""

    overall_summary: str = Field(min_length=1)


@traced("resume.analyze")
def analyze_resume(
    resume: CandidateResume,
) -> ResumeAnalysis:
    """
    Analyze resume evidence across InterviewGapAI competencies.

    This function evaluates evidence contained in the resume.
    It does NOT determine actual candidate skill level.

    The seven competency assessments are independent readings of the same
    resume, so they are requested concurrently. Asking one model call for all
    seven made the stage as slow as the sum of their output; asking seven
    calls for one each makes it as slow as the longest single assessment.
    """

    # Pass the extracted candidate facts, not the synthetic fixture manifest.
    # Supplying expected labels here would bias the evidence assessment.
    resume_json = resume.model_dump_json(indent=2)

    # Each worker needs its own context copy: a Context cannot be entered by
    # two threads at once, and without one the child spans would start a new
    # trace instead of nesting under this stage.
    with ThreadPoolExecutor(
        max_workers=len(COMPETENCIES) + 1,
        thread_name_prefix="ig-analyze",
    ) as pool:
        summary_call = pool.submit(
            copy_context().run, _summarize, resume_json, resume.candidate_id,
        )
        evidence_calls = [
            pool.submit(
                copy_context().run,
                _assess_competency,
                resume_json,
                resume.candidate_id,
                competency,
            )
            for competency in COMPETENCIES
        ]

        # Read in competency order rather than completion order so the
        # assembled analysis does not depend on which call finished first.
        competency_evidence = [call.result() for call in evidence_calls]
        overall_summary = summary_call.result()

    return ResumeAnalysis(
        # candidate_id is application-owned data.
        candidate_id=resume.candidate_id,
        overall_summary=overall_summary,
        competency_evidence=competency_evidence,
    )


def _assess_competency(
    resume_json: str,
    candidate_id: str,
    competency: Competency,
) -> CompetencyEvidence:
    """Assess one competency's resume evidence."""

    with trace_span("resume.analyze.competency", competency=competency.value):
        # The model interprets evidence and suggests probing priorities. Schema
        # validation checks structure; it does not prove those judgments correct.
        response = call_with_retry(
            lambda: client.responses.parse(
                model=ANALYSIS_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": COMPETENCY_EVIDENCE_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": f"""
Analyze the following CandidateResume for one competency only.

Candidate ID: {candidate_id}
Competency: {competency.value}

CANDIDATE RESUME
----------------
{resume_json}
----------------

Return the CompetencyEvidence assessment for {competency.value}.
""",
                    },
                ],
                text_format=CompetencyEvidence,
            ),
            max_retries=ANALYSIS_MAX_RETRIES,
        )

    assessment = response.output_parsed

    if assessment is None:
        raise ValueError(
            f"Resume analysis failed for candidate {candidate_id} "
            f"on competency: {competency.value}"
        )

    # Which competency was asked for is application-owned. Fixing it here keeps
    # a mislabelled response from silently duplicating one competency and
    # dropping another from the assembled analysis.
    assessment.competency = competency

    return assessment


def _summarize(resume_json: str, candidate_id: str) -> str:
    """Produce the evidence-focused overall summary."""

    with trace_span("resume.analyze.summary"):
        response = call_with_retry(
            lambda: client.responses.parse(
                model=ANALYSIS_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": RESUME_SUMMARY_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": f"""
Summarize the following CandidateResume.

Candidate ID: {candidate_id}

CANDIDATE RESUME
----------------
{resume_json}
----------------
""",
                    },
                ],
                text_format=_ResumeSummary,
            ),
            max_retries=ANALYSIS_MAX_RETRIES,
        )

    summary = response.output_parsed

    if summary is None:
        raise ValueError(
            f"Resume analysis failed for candidate: {candidate_id}"
        )

    return summary.overall_summary
