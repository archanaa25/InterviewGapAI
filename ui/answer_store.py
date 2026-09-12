"""
Persist a completed interview so the interviewer can read it afterwards.

Until now answers lived only in the Streamlit session that collected them, so
an interviewer signing in later could never see what a candidate wrote. That
is the gap this closes.

Where, and why it matters
-------------------------
Runs are written under data/runs/, which is git-ignored. Candidate answers are
the candidate's own words: unlike the synthetic fixtures under data/prepared/,
they must not land in the repository. The directory is created on first write
and nothing here ever touches data/prepared/.

What is stored
--------------
The question ids asked, what the candidate wrote, and whether each was
skipped - enough for an interviewer to read the interview and for a future
evaluation stage to score it. The candidate id is already an opaque content
hash of the uploaded file (upload-<sha16>), not a name.

What is NOT stored
------------------
No expected concepts, no rubric, no evaluation. This module records what
happened; it does not judge it, and the backend has no scorer yet.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = PROJECT_ROOT / "data" / "runs"

SCHEMA_VERSION = 1


class AnswerStoreError(RuntimeError):
    """Raised when a completed interview could not be written."""


def _run_path(candidate_id: str) -> Path:
    # candidate_id is our own opaque id, but it reaches here from an upload,
    # so it is never trusted as a path component.
    safe = "".join(
        character
        for character in str(candidate_id)
        if character.isalnum() or character in {"-", "_"}
    )
    if not safe:
        raise AnswerStoreError("Candidate id produced no usable filename.")
    return RUN_DIR / f"{safe}.json"


def save_intake(prepared: Any) -> Path:
    """
    Write the intake as soon as the plan exists, before any interview starts.

    Recording only from the interview onwards meant a candidate who had
    uploaded a resume and was reading their plan did not exist as far as
    another tab was concerned - which is the first moment someone would
    reasonably look.

    Question selection has not run yet, so this stores four stages and no
    answers. save_run overwrites it with the fuller record later.
    """

    candidate_id = prepared.plan.candidate_id

    payload = {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "submitted": False,
        "answered": 0,
        "skipped": 0,
        "total": None,
        "upload": _upload_record(prepared.upload),
        "stages": {
            "resume extraction": prepared.resume.model_dump(mode="json"),
            "resume evidence": prepared.analysis.model_dump(mode="json"),
            "interview plan": prepared.plan.model_dump(mode="json"),
        },
        "answers": [],
    }

    return _write(candidate_id, payload)


def _upload_record(upload: Any) -> dict:
    """Non-content provenance for the uploaded file."""

    return {
        "filename": upload.filename,
        "format": getattr(upload.format, "value", str(upload.format)),
        "media_type": upload.media_type,
        "size_bytes": upload.size_bytes,
        "sha256": upload.sha256,
        "candidate_id": upload.candidate_id,
        "extraction_method": upload.extraction_method,
        "characters_extracted": len(upload.text),
        "warnings": list(upload.warnings),
    }


def _write(candidate_id: str, payload: dict) -> Path:
    """Write one run, creating the directory on first use."""

    try:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        path = _run_path(candidate_id)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        raise AnswerStoreError(
            f"Could not write the interview record: {type(error).__name__}"
        ) from error

    return path


def save_run(intake: Any, progress: Any) -> Path:
    """
    Write one completed interview and return its path.

    Raises AnswerStoreError rather than failing silently: a submitted
    interview that was not recorded is worth surfacing, not swallowing.
    """

    questions = {
        question.question_id: question for question in intake.question_set.questions
    }
    candidate_id = intake.plan.candidate_id

    payload = {
        "schema_version": SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "submitted": bool(progress.submitted),
        "answered": progress.answered_count,
        "skipped": progress.skipped_count,
        "total": len(progress.question_ids),
        "upload": _upload_record(intake.upload),
        # Every earlier stage is stored too. Only fixture candidates have
        # files under data/prepared/; a real upload has none, so without
        # these an interviewer in a different browser session would see an
        # interview's answers with no resume, evidence or plan behind them.
        "stages": {
            "resume extraction": intake.resume.model_dump(mode="json"),
            "resume evidence": intake.analysis.model_dump(mode="json"),
            "interview plan": intake.plan.model_dump(mode="json"),
            "interview questions": intake.question_set.model_dump(mode="json"),
        },
        "answers": [
            {
                "position": position,
                "question_id": answer.question_id,
                # The question text is copied in so the run reads on its own
                # even if the corpus is re-curated later.
                "question": getattr(questions.get(answer.question_id), "question", None),
                "competency": getattr(
                    getattr(questions.get(answer.question_id), "competency", None),
                    "value",
                    None,
                ),
                "difficulty": getattr(
                    questions.get(answer.question_id), "difficulty", None
                ),
                "skipped": answer.skipped,
                "characters": len(answer.text),
                "text": answer.text,
            }
            for position, answer in enumerate(progress.answers, start=1)
        ],
    }

    return _write(candidate_id, payload)


def load_run(candidate_id: str) -> dict | None:
    """One saved interview, or None when nothing was recorded for it."""

    try:
        path = _run_path(candidate_id)
    except AnswerStoreError:
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def saved_runs() -> list[str]:
    """Candidate ids with a recorded interview, newest first."""

    if not RUN_DIR.is_dir():
        return []

    paths = [path for path in RUN_DIR.glob("*.json") if path.is_file()]
    paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [path.stem for path in paths]


__all__ = [
    "AnswerStoreError",
    "save_intake",
    "RUN_DIR",
    "SCHEMA_VERSION",
    "load_run",
    "save_run",
    "saved_runs",
]
