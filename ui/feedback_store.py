"""
Capture an interviewer's live thumbs up/down on an Evaluation Agent
judgement, read from the Intake traces panel.

Every other eval artifact under data/eval/ scores the pipeline against a
fixed golden set. This instead records a signal on a judgement the pipeline
made about a real candidate, as an interviewer actually reads it - the
human half of online eval. Written under data/runs/ (git-ignored, like every
other candidate record) rather than data/eval/, because a feedback row names
a candidate_id and sits one hop from the excerpt of their answer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = PROJECT_ROOT / "data" / "runs" / "_feedback.jsonl"


def save_feedback(
    *,
    candidate_id: str,
    question_id: str,
    concept: str,
    rating: str,
    note: str | None = None,
) -> None:
    """Append one feedback row. rating is 'up' or 'down'."""

    if rating not in {"up", "down"}:
        raise ValueError(f"Unknown rating: {rating!r}")

    row = {
        "candidate_id": candidate_id,
        "question_id": question_id,
        "concept": concept,
        "rating": rating,
        "note": note,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_feedback() -> list[dict[str, Any]]:
    """Every recorded feedback row, oldest first, or [] if none exist yet."""

    if not FEEDBACK_PATH.is_file():
        return []

    rows: list[dict[str, Any]] = []
    for line in FEEDBACK_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


__all__ = ["FEEDBACK_PATH", "load_feedback", "save_feedback"]
