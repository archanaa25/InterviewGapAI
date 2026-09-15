"""
Score real, already-judged interviews under data/runs/ with an LLM judge.

Every other script under scripts/evaluate_*.py scores the pipeline against a
fixed golden set or synthetic fixtures. This is the online counterpart: it
samples concept judgements the Evaluation Agent made on actual candidates
and asks an independent model whether it agrees. Results land in
data/eval/online_judge_results.jsonl and feed the "Online judge" dashboard
panel (ui/dashboard.py). That output file is git-ignored: its "reason" field
quotes fragments of a real candidate's own answer, the same reason
data/runs/ itself stays out of the repository.

--limit caps how many concept judgements are sent to the LLM in one run, so
a demo or a quick check does not wait on (or pay for) every judgement on
disk.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.online_judge import JUDGE_PROVIDER, MODEL, judge_production_verdict


RUNS_DIR = PROJECT_ROOT / "data" / "runs"

OUTPUT_FILE = PROJECT_ROOT / "data" / "eval" / "online_judge_results.jsonl"


def load_runs():
    """Every recorded interview under data/runs/, oldest write first."""

    if not RUNS_DIR.is_dir():
        return []

    runs = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            runs.append(payload)
    return runs


def question_text(run: dict, question_id: str) -> str:
    for answer in run.get("answers") or []:
        if answer.get("question_id") == question_id:
            return answer.get("question") or ""
    return ""


def judged_items(run: dict):
    """One item per (question, concept judgement) worth auditing."""

    evaluation = run.get("evaluation") or {}
    questions = (evaluation.get("result") or {}).get("questions") or []

    for question in questions:
        if question.get("status") != "EVALUATED":
            continue
        for judgement in question.get("concept_judgements") or []:
            yield question, judgement


def already_judged() -> set[tuple[str, str, str]]:
    """(candidate, question, concept) triples already in the output file."""

    if not OUTPUT_FILE.is_file():
        return set()

    seen = set()
    for line in OUTPUT_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        seen.add((row.get("candidate_id"), row.get("question_id"), row.get("concept")))
    return seen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=15,
        help="Maximum number of concept judgements to send to the LLM (default: 15).",
    )
    parser.add_argument(
        "--candidate",
        default=None,
        help="Only judge this candidate_id (default: all recorded candidates).",
    )
    args = parser.parse_args()

    runs = load_runs()
    if args.candidate:
        runs = [run for run in runs if run.get("candidate_id") == args.candidate]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    skip = already_judged()
    results = []
    processed = 0

    print(f"Judge provider/model : {JUDGE_PROVIDER} / {MODEL}")
    print(f"Recorded interviews  : {len(runs)}")
    print(f"Already judged       : {len(skip)}")
    print(f"Limit                : {args.limit}\n")

    for run in runs:
        candidate_id = run.get("candidate_id")

        for question, judgement in judged_items(run):
            if processed >= args.limit:
                break

            question_id = question.get("question_id")
            concept = judgement.get("concept")

            if (candidate_id, question_id, concept) in skip:
                continue

            processed += 1
            print(f"[{processed}/{args.limit}] {candidate_id} · {question_id} · {concept}")

            try:
                verdict = judge_production_verdict(
                    question_id=question_id,
                    question=question_text(run, question_id),
                    concept=concept,
                    original_status=judgement.get("status"),
                    rationale=judgement.get("rationale") or "",
                    answer_excerpt=judgement.get("answer_excerpt") or "",
                )
            except Exception as error:
                print(f"    skipped ({type(error).__name__}: {error})")
                continue

            results.append(
                {
                    "candidate_id": candidate_id,
                    "question_id": question_id,
                    "concept": concept,
                    "original_status": judgement.get("status"),
                    "agreement": verdict.agreement.value,
                    "faithfulness_score": verdict.faithfulness_score,
                    "reason": verdict.reason,
                    "judge_provider": JUDGE_PROVIDER,
                    "judge_model": MODEL,
                    "judged_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        if processed >= args.limit:
            break

    with OUTPUT_FILE.open("a", encoding="utf-8") as handle:
        for record in results:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    disagreements = [row for row in results if row["agreement"] == "DISAGREE"]
    mean_score = (
        sum(row["faithfulness_score"] for row in results) / len(results)
        if results
        else 0.0
    )

    print("\n" + "=" * 70)
    print("ONLINE JUDGE — PRODUCTION SAMPLE")
    print("=" * 70)
    print(f"Judged        : {len(results)}")
    print(f"Disagreements : {len(disagreements)}")
    print(f"Mean score    : {mean_score:.2f}/5")
    print(f"\nAppended to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
