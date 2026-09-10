import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from src.schemas.resume import CandidateResume
from src.resume.prompts import RESUME_EXTRACTION_SYSTEM_PROMPT


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_resume(
    resume_text: str,
    candidate_id: str,
) -> CandidateResume:
    """
    Convert raw resume text into a validated CandidateResume object.

    This stage performs factual extraction only.
    It does not perform competency assessment.
    """

    # The schema captures stated facts only; competency judgments belong to
    # the analyzer stage. Structured parsing validates the returned field types.
    response = client.responses.parse(
        model="gpt-5.6",
        input=[
            {
                "role": "system",
                "content": RESUME_EXTRACTION_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
Candidate ID: {candidate_id}

Extract the following resume into the CandidateResume schema.

RESUME:
----------------
{resume_text}
----------------
""",
            },
        ],
        text_format=CandidateResume,
    )

    resume = response.output_parsed

    # A response can lack a parsed object (for example, a refusal). Fail before
    # downstream code attempts to save or analyze an unusable result.
    if resume is None:
        raise ValueError(
            f"Resume extraction failed for candidate: {candidate_id}"
        )

    # candidate_id comes from our application, not the LLM.
    resume.candidate_id = candidate_id

    return resume


def extract_resume_file(path: Path) -> CandidateResume:
    """Read a Markdown resume and extract its structured representation."""

    resume_text = path.read_text(encoding="utf-8")

    # Use the filename as the stable identity across extraction, analysis,
    # and planning, rather than relying on a generated name or identifier.
    candidate_id = path.stem

    return extract_resume(
        resume_text=resume_text,
        candidate_id=candidate_id,
    )