"""Resume-upload helpers; importing this module does not create API clients."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

from .core import flush_telemetry, log_event, request_context, trace_span


def read_uploaded_resume(filename, content):
    """Read UTF-8 text or a text PDF; never persist the uploaded filename."""
    data = bytes(content)
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError("Upload a nonempty resume smaller than 10 MiB.")
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("Save the resume as UTF-8 text and upload it again.") from None
    elif suffix == ".pdf":
        executable = shutil.which("pdftotext")
        if not executable:
            raise ValueError("PDF support requires pdftotext (Poppler). Upload TXT or Markdown instead.")
        with tempfile.TemporaryDirectory(prefix="resume-upload-") as directory:
            source = Path(directory) / "resume.pdf"
            target = Path(directory) / "resume.txt"
            source.write_bytes(data)
            try:
                subprocess.run(
                    [executable, "-layout", str(source), str(target)],
                    check=True, capture_output=True, timeout=30,
                )
                text = target.read_text(encoding="utf-8")
            except (subprocess.SubprocessError, UnicodeError):
                raise ValueError("Cannot read this PDF. Upload a text-based PDF or UTF-8 text.") from None
    else:
        raise ValueError("Supported resume formats: .txt, .md, .pdf.")
    text = text.strip()
    if not text:
        raise ValueError("No resume text found. Scanned PDFs need OCR before upload.")
    return text


def run_resume_intake(resume_text, *, interview_id=None, include_interview=False):
    """Run a new resume under one trace; return models locally, metadata remotely."""
    if not isinstance(resume_text, str) or not resume_text.strip():
        raise ValueError("Resume text must not be empty.")
    interview_id = interview_id or f"intake-{uuid4().hex}"
    result = {}
    try:
        with request_context(interview_id=interview_id) as ids:
            result.update(ids)
            with trace_span("intake.resume", include_interview=include_interview) as span:
                # Lazy imports allow upload/credential setup before client creation.
                from src.resume.extractor import extract_resume
                from src.resume.analyzer import analyze_resume

                resume = extract_resume(resume_text, candidate_id=f"candidate-{uuid4().hex}")
                analysis = analyze_resume(resume)
                result.update(resume=resume, analysis=analysis)
                span.set_attributes(competencies_assessed=len(analysis.competency_evidence))
                if include_interview:
                    from src.planning.interview_planner import create_interview_plan
                    from src.interview.question_selector import select_interview_questions

                    plan = create_interview_plan(analysis)
                    questions = select_interview_questions(plan)
                    result.update(plan=plan, question_set=questions)
                    span.set_attributes(question_count=len(questions.questions), is_complete=questions.is_complete)
    finally:
        flush_telemetry(timeout=5.0)
    return result


def get_trace_url(trace_id):
    """Resolve an authenticated dashboard URL after export; never share publicly.

    May return None while a run is being ingested, or if export/authentication
    failed. Retry this lookup separately instead of repeating the LLM pipeline.
    """
    try:
        from langsmith.run_trees import get_cached_client

        client = get_cached_client()
        run = client.read_run(trace_id)
        return client.get_run_url(run=run)
    except Exception as exc:
        log_event("telemetry.dashboard_lookup_failed", level="WARNING", error_type=type(exc).__name__)
        return None
