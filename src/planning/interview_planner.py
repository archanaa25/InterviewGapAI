import os

from dotenv import load_dotenv
from openai import OpenAI

from src.schemas.resume_analysis import ResumeAnalysis
from src.schemas.interview_plan import InterviewPlan
from src.planning.prompts import INTERVIEW_PLANNING_SYSTEM_PROMPT


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
    analysis_json = resume_analysis.model_dump_json(indent=2)

    # The model proposes allocations; InterviewPlan validators enforce their
    # arithmetic consistency. Actual corpus questions are selected later.
    response = client.responses.parse(
        model="gpt-5.6",
        input=[
            {
                "role": "system",
                "content": INTERVIEW_PLANNING_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
Create an InterviewPlan for the following candidate.

Candidate ID: {resume_analysis.candidate_id}

RESUME ANALYSIS
---------------
{analysis_json}
---------------

Create a balanced interview plan containing exactly 10 questions.

Remember:

- This is a PLAN only.
- Do not generate actual interview questions.
- Competency allocations must total exactly 10.
- Difficulty allocations must total exactly 10.
- Missing resume evidence is not candidate weakness.
""",
            },
        ],
        text_format=InterviewPlan,
    )

    plan = response.output_parsed

    if plan is None:
        raise ValueError(
            f"Interview planning failed for candidate: "
            f"{resume_analysis.candidate_id}"
        )

    # Candidate ID is application-owned.
    plan.candidate_id = resume_analysis.candidate_id

    return plan
