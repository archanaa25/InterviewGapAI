import os

from dotenv import load_dotenv
from openai import OpenAI

from src.schemas.resume import CandidateResume
from src.schemas.resume_analysis import ResumeAnalysis
from src.resume.analyzer_prompts import RESUME_ANALYSIS_SYSTEM_PROMPT
from src.observability import traced


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@traced("resume.analyze")
def analyze_resume(
    resume: CandidateResume,
) -> ResumeAnalysis:
    """
    Analyze resume evidence across InterviewGapAI competencies.

    This function evaluates evidence contained in the resume.
    It does NOT determine actual candidate skill level.
    """

    # Pass the extracted candidate facts, not the synthetic fixture manifest.
    # Supplying expected labels here would bias the evidence assessment.
    resume_json = resume.model_dump_json(indent=2)

    # The model interprets evidence and suggests probing priorities. Schema
    # validation checks structure; it does not prove those judgments correct.
    response = client.responses.parse(
        model="gpt-5.6",
        input=[
            {
                "role": "system",
                "content": RESUME_ANALYSIS_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
Analyze the following CandidateResume.

Candidate ID: {resume.candidate_id}

CANDIDATE RESUME
----------------
{resume_json}
----------------

Return a ResumeAnalysis containing exactly one assessment
for each supported competency.
""",
            },
        ],
        text_format=ResumeAnalysis,
    )

    analysis = response.output_parsed

    if analysis is None:
        raise ValueError(
            f"Resume analysis failed for candidate: {resume.candidate_id}"
        )

    # candidate_id is application-owned data.
    analysis.candidate_id = resume.candidate_id

    return analysis
