import os
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from src.schemas.resume_analysis import ResumeAnalysis
from src.schemas.interview_plan import (
    CompetencyTarget,
    DifficultyDistribution,
    InterviewPlan,
    InterviewStrategy,
)
from src.planning.prompts import INTERVIEW_PLANNING_SYSTEM_PROMPT
from src.observability import traced, log_event
from src.llm_client import build_client
from src.llm_retry import call_with_retry


load_dotenv()

# Overridable so a model change is a config rollback, not a code change.
# LLM_PROVIDER=deepseek switches the client and this default together; an
# explicit INTERVIEW_PLANNING_MODEL still wins over either provider's default.
client, _default_model = build_client("gpt-5.6")
PLANNING_MODEL = os.getenv("INTERVIEW_PLANNING_MODEL", _default_model)

# An allocation that totals 9 instead of 10 is an arithmetic slip, not a
# judgement the model would defend. Showing it the arithmetic and asking again
# fixes it; failing the stage costs the candidate the whole intake.
PLANNING_ATTEMPTS = 3


class _PlanAllocation(BaseModel):
    """
    The part of an InterviewPlan the model actually decides.

    difficulty_distribution and total_questions are sums of the per-competency
    allocation, so asking the model to restate them cost output tokens and
    added a failure mode: a plan whose summary disagreed with its own targets
    was rejected by InterviewPlan's validators after it had been paid for.
    """

    competency_targets: List[CompetencyTarget]

    rationale: str = Field(
        ...,
        min_length=1,
        description="Overall difficulty strategy, at most 40 words.",
    )


@traced("interview.plan")
def create_interview_plan(
    resume_analysis: ResumeAnalysis,
) -> InterviewPlan:
    """
    Create a constrained 10-question interview plan from ResumeAnalysis.

    The LLM decides the interview strategy.

    Pydantic validates deterministic constraints such as:
    - exactly 10 questions
    - difficulty total = 10
    - competency allocation total = 10
    - no duplicate competencies
    """

    # Planning consumes evidence assessments, not inferred skill-gap scores.
    # Missing resume evidence remains a reason to ask questions.
    #
    # Only the fields that drive an allocation are sent. The full analysis JSON
    # carried every evidence item and its source, which the allocation decision
    # never reads, and each one had to be processed before the first output
    # token appeared.
    digest = _evidence_digest(resume_analysis)

    request = f"""
Create an InterviewPlan for the following candidate.

Candidate ID: {resume_analysis.candidate_id}

RESUME EVIDENCE
---------------
{digest}
---------------

Create a balanced interview plan containing exactly 10 questions.

Remember:

- This is a PLAN only.
- Do not generate actual interview questions.
- Competency allocations must total exactly 10.
- Missing resume evidence is not candidate weakness.
"""

    correction = ""

    for attempt in range(PLANNING_ATTEMPTS):
        allocation = _request_allocation(
            resume_analysis.candidate_id, request + correction,
        )
        targets = allocation.competency_targets
        allocated = sum(target.question_count for target in targets)

        try:
            # The model proposes allocations; InterviewPlan validators enforce
            # their arithmetic consistency. Corpus questions are selected later.
            return InterviewPlan(
                # Candidate ID is application-owned.
                candidate_id=resume_analysis.candidate_id,
                total_questions=allocated,
                competency_targets=targets,
                difficulty_distribution=DifficultyDistribution(
                    basic=sum(target.basic for target in targets),
                    intermediate=sum(target.intermediate for target in targets),
                    advanced=sum(target.advanced for target in targets),
                ),
                strategy=InterviewStrategy(rationale=allocation.rationale),
            )
        except ValidationError:
            if attempt == PLANNING_ATTEMPTS - 1:
                raise
            log_event(
                "interview.plan.reallocated",
                level="WARNING",
                allocated=allocated,
                attempt=attempt + 1,
            )
            # Naming the shortfall alone was not enough to fix it. Showing the
            # model its own per-competency counts back, with the arithmetic
            # done, gives it something to correct rather than recompute.
            correction = f"""
YOUR PREVIOUS ALLOCATION WAS REJECTED

{_allocation_breakdown(targets)}

Total: {allocated} questions. It must be exactly 10.

{_correction_instruction(allocated)}

Return the full allocation again, corrected.
"""


def _request_allocation(candidate_id: str, request: str) -> _PlanAllocation:
    """Ask the planner for one allocation."""

    response = call_with_retry(
        lambda: client.responses.parse(
            model=PLANNING_MODEL,
            input=[
                {"role": "system", "content": INTERVIEW_PLANNING_SYSTEM_PROMPT},
                {"role": "user", "content": request},
            ],
            text_format=_PlanAllocation,
        )
    )

    allocation = response.output_parsed

    if allocation is None:
        raise ValueError(
            f"Interview planning failed for candidate: {candidate_id}"
        )

    return allocation


def _allocation_breakdown(targets: List[CompetencyTarget]) -> str:
    """Render a rejected allocation with its per-competency arithmetic shown."""

    return "\n".join(
        f"- {target.competency.value}: {target.question_count} "
        f"(basic {target.basic}, intermediate {target.intermediate}, "
        f"advanced {target.advanced})"
        for target in targets
    )


def _correction_instruction(allocated: int) -> str:
    """Say which way to move and by how much, rather than restating the rule."""

    if allocated < 10:
        missing = 10 - allocated
        return (
            f"Add {missing} more question(s), to the competencies with the "
            f"highest probe priority. Leave every other count unchanged."
        )
    if allocated > 10:
        excess = allocated - 10
        return (
            f"Remove {excess} question(s), from the competencies with the "
            f"lowest probe priority. Every competency must keep at least one."
        )
    return "Keep the totals at 10 and correct the per-competency arithmetic."


def _evidence_digest(resume_analysis: ResumeAnalysis) -> str:
    """Render the allocation-relevant fields of an analysis as compact lines."""

    return "\n".join(
        f"- {item.competency.value}: {item.evidence_level.value}, "
        f"probe_priority={item.probe_priority.value} — {item.reason}"
        for item in resume_analysis.competency_evidence
    )
