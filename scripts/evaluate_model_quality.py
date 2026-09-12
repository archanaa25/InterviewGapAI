"""
Score the resume analyzer's quality per model, not just per pipeline shape.

The intake latency harness answers "is it faster". This one answers the
question that decides whether a faster model is usable: does it still read a
resume correctly? Both are needed - a model that halves latency and starts
crediting competencies a resume never evidenced has made the product worse,
because the interview then skips a probe it should have made.

Scoring is the shipped scorecard's, imported rather than reimplemented, so a
model arm and the committed baseline are judged by identical rules.

Arms are (provider, model) pairs. Each one re-analyzes every prepared resume
through the real analyzer with that arm configured, so the fan-out, the
prompts and the retry policy under test are the ones that ship.

    RESUME_ANALYSIS_MODEL and LLM_PROVIDER are set per arm inside this
    process. Nothing is written to .env and the committed analyses under
    data/prepared/resume_analysis/ are never overwritten.

Writes data/eval/model_quality_comparison.json for the interviewer dashboard.

Usage:
    uv run python scripts/evaluate_model_quality.py
    uv run python scripts/evaluate_model_quality.py --arms deepseek:deepseek-chat
    uv run python scripts/evaluate_model_quality.py --candidates 3
"""

import argparse
import importlib
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.schemas.resume import CandidateResume

# The shipped scorecard's rules, imported so both arms are judged identically.
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "shipped_scorecard", PROJECT_ROOT / "scripts" / "evaluate_resume_analysis.py"
)
_scorecard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_scorecard)

RESUME_DIR = PROJECT_ROOT / "data" / "prepared" / "resumes"
REPORT_PATH = PROJECT_ROOT / "data" / "eval" / "model_quality_comparison.json"

# provider:model. DeepSeek is the candidate; the OpenAI arms are the reference
# the corpus labels were established against.
DEFAULT_ARMS = (
    "deepseek:deepseek-chat",
    "openai:gpt-5.4",
    "openai:gpt-5.6",
)

RULE = "=" * 78


def parse_arm(spec: str) -> tuple[str, str]:
    provider, _, model = spec.partition(":")
    if not provider or not model:
        raise SystemExit(f"Arm must look like provider:model, got {spec!r}")
    return provider, model


def analyze_with(provider: str, model: str, resumes: list[CandidateResume]):
    """
    Re-analyze every resume with one arm configured.

    The analyzer binds its client and model at import time, so the module is
    reloaded per arm rather than patched: that exercises the same construction
    path a deployment takes when these variables are set in its environment.
    """

    previous = {
        key: os.environ.get(key)
        for key in ("LLM_PROVIDER", "RESUME_ANALYSIS_MODEL")
    }
    os.environ["LLM_PROVIDER"] = provider
    os.environ["RESUME_ANALYSIS_MODEL"] = model

    try:
        import src.resume.analyzer as analyzer

        analyzer = importlib.reload(analyzer)

        analyses, durations, failures = [], [], []

        for resume in resumes:
            started = time.perf_counter()
            try:
                analyses.append(analyzer.analyze_resume(resume))
                durations.append(time.perf_counter() - started)
            except Exception as error:
                # One candidate failing must not discard the arm: record it
                # and score what did come back, or a flaky provider looks
                # identical to an inaccurate one.
                failures.append(
                    {"candidate_id": resume.candidate_id, "error": type(error).__name__}
                )
                print(f"      {resume.candidate_id}: {type(error).__name__}", flush=True)

        return analyses, durations, failures
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def score(analyses, expected_by_candidate) -> tuple[dict, list[dict]]:
    rows = []
    for analysis in analyses:
        expected = expected_by_candidate.get(analysis.candidate_id)
        if expected is None:
            continue
        rows.extend(_scorecard.score_candidate(analysis, expected))
    return _scorecard.summarise(rows) if rows else {}, rows


def _git_ref() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arms", nargs="*", default=list(DEFAULT_ARMS),
        help="provider:model pairs to score.",
    )
    parser.add_argument(
        "--candidates", type=int, default=0,
        help="Limit the number of resumes (0 = all).",
    )
    args = parser.parse_args()

    expected_by_candidate = _scorecard.load_manifest()

    paths = sorted(RESUME_DIR.glob("candidate_*.json"))
    if args.candidates:
        paths = paths[: args.candidates]
    if not paths:
        raise SystemExit(f"No prepared resumes under {RESUME_DIR}")

    resumes = [CandidateResume.model_validate_json(p.read_text()) for p in paths]
    print(f"{len(resumes)} resumes · {len(args.arms)} arms")

    results = []

    for spec in args.arms:
        provider, model = parse_arm(spec)
        print(f"  {spec} ...", flush=True)

        analyses, durations, failures = analyze_with(provider, model, resumes)

        if not analyses:
            results.append(
                {
                    "arm": spec, "provider": provider, "model": model,
                    "error": "every candidate failed",
                    "failures": failures,
                }
            )
            continue

        summary, rows = score(analyses, expected_by_candidate)

        results.append(
            {
                "arm": spec,
                "provider": provider,
                "model": model,
                "candidates_scored": len(analyses),
                "candidates_attempted": len(resumes),
                "failures": failures,
                **summary,
                "median_seconds": statistics.median(durations) if durations else None,
                "total_seconds": sum(durations),
                # Kept so a surprising score can be traced to its judgements
                # rather than taken on faith.
                "judgement_rows": rows,
            }
        )

    ranked = [row for row in results if row.get("accuracy") is not None]
    ranked.sort(key=lambda row: row["accuracy"], reverse=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_ref": _git_ref(),
        "scored_against": "data/synthetic/resume_manifest.json",
        "stage": "resume analysis",
        "candidates": [path.stem for path in paths],
        "arms": results,
        "best_accuracy": ranked[0]["arm"] if ranked else None,
        "notes": [
            "Accuracy alone does not decide this. Over-credit means the "
            "analyzer claimed evidence a resume did not give, so the "
            "interview skips a probe it should have made; under-credit only "
            "wastes a question on known ground. An arm with equal accuracy "
            "and fewer over-credits is the better arm.",
            "Only the analysis stage varies here. Extraction and planning are "
            "left at their configured models, so this isolates one stage.",
            "Retrieval quality cannot appear in this table: it depends on the "
            "embedding model, not the chat model, and DeepSeek exposes no "
            "embeddings endpoint.",
        ],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print()
    print(RULE)
    print("RESUME ANALYSIS QUALITY BY MODEL".center(78))
    print(RULE)
    header = (
        f"{'ARM':<26}{'ACC':>7}{'PREC':>7}{'RECALL':>8}"
        f"{'OVER':>6}{'UNDER':>7}{'MED s':>8}{'SCORED':>8}"
    )
    print(header)
    print("-" * 78)
    for row in results:
        if row.get("accuracy") is None:
            print(f"{row['arm']:<26}{'failed':>7}  {row.get('error', '')}")
            continue
        counts = row["counts"]
        print(
            f"{row['arm']:<26}{row['accuracy']:>6.1%}{row['precision']:>7.1%}"
            f"{row['recall']:>8.1%}{counts['over_credit']:>6}"
            f"{counts['under_credit']:>7}{row['median_seconds']:>8.1f}"
            f"{row['candidates_scored']:>4}/{row['candidates_attempted']}"
        )
    print("-" * 78)
    for note in report["notes"]:
        print(f"  · {' '.join(note.split())}")
    print()
    print(f"Report written to {REPORT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
