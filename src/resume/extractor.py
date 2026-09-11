import os
from pathlib import Path

from dotenv import load_dotenv

from src.schemas.resume import CandidateResume
from src.resume.prompts import RESUME_EXTRACTION_SYSTEM_PROMPT
from src.observability import traced
from src.llm_client import build_client
from src.llm_retry import call_with_retry


load_dotenv()

# Extraction is transcription into a schema, not judgement: it spends no
# reasoning tokens even on the largest model, so a smaller one returns the
# same fields sooner. Overridable so a model change is a config rollback.
# LLM_PROVIDER=deepseek switches the client and this default together; an
# explicit RESUME_EXTRACTION_MODEL still wins over either provider's default.
client, _default_model = build_client("gpt-5.4-mini")
EXTRACTION_MODEL = os.getenv("RESUME_EXTRACTION_MODEL", _default_model)


@traced("resume.extract")
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
    response = call_with_retry(
        lambda: client.responses.parse(
            model=EXTRACTION_MODEL,
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
