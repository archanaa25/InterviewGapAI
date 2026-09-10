"""
Score the Resume Analyzer against known fixture labels.

The synthetic manifest records which competencies each resume was written to
evidence. Everything unlisted was written to be silent. That makes the
manifest a labelled dataset for stage 2.

Two error types matter, and they are not equally bad:

  over-credit   The resume is silent, but the analyzer claims evidence.
                The interview then fails to probe an area it should have,
                and the candidate is credited for something unproven.

  under-credit  The resume shows evidence, but the analyzer reports unknown.
                The interview spends questions re-checking known ground.
                Wasteful, but safe by design.

Usage:
    uv run python scripts/evaluate_resume_analysis.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.resume_analysis import ResumeAnalysis

MANIFEST_PATH = PROJECT_ROOT / "data/synthetic/resume_manifest.json"
ANALYSIS_DIR = PROJECT_ROOT / "data/prepared/resume_analysis"
REPORT_PATH = PROJECT_ROOT / "data/eval/resume_analysis_scorecard.json"

# The analyzer's three levels collapse to a binary question: did the resume
# say anything about this competency at all?
EVIDENCE_LEVELS = {"DEMONSTRATED", "PARTIAL_EVIDENCE"}

RULE = "=" * 78


def load_manifest():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    return {
        candidate["candidate_id"]: set(candidate["evidence_expected_for"])
        for candidate in manifest["candidates"]
    }


def score_candidate(analysis: ResumeAnalysis, expected: set):
    """Compare one analysis against its manifest labels."""

    rows = []

    for item in analysis.competency_evidence:

        competency = item.competency.value
        level = item.evidence_level.value

        label_expected = competency in expected
        label_actual = level in EVIDENCE_LEVELS

        if label_expected and label_actual:
            outcome = "correct_evidence"
        elif not label_expected and not label_actual:
            outcome = "correct_unknown"
        elif label_actual and not label_expected:
            outcome = "over_credit"
        else:
            outcome = "under_credit"

        rows.append(
            {
                "candidate_id": analysis.candidate_id,
                "competency": competency,
                "expected": "evidence" if label_expected else "unknown",
                "actual_level": level,
                "probe_priority": item.probe_priority.value,
                "confidence": item.confidence,
                "outcome": outcome,
            }
        )

    return rows


def summarise(rows):
    counts = {
        "correct_evidence": 0,
        "correct_unknown": 0,
        "over_credit": 0,
        "under_credit": 0,
    }

    for row in rows:
        counts[row["outcome"]] += 1

    total = len(rows)
    correct = counts["correct_evidence"] + counts["correct_unknown"]

    # Precision and recall are stated over the "evidence" class: of the
    # competencies the analyzer credited, how many were really evidenced,
    # and of those really evidenced, how many did it find?
    predicted_evidence = counts["correct_evidence"] + counts["over_credit"]
    actual_evidence = counts["correct_evidence"] + counts["under_credit"]

    return {
        "judgements": total,
        "accuracy": correct / total if total else 0.0,
        "precision": (
            counts["correct_evidence"] / predicted_evidence
            if predicted_evidence
            else 0.0
        ),
        "recall": (
            counts["correct_evidence"] / actual_evidence
            if actual_evidence
            else 0.0
        ),
        "counts": counts,
    }


def main():

    expected_by_candidate = load_manifest()

    rows = []
    skipped = []

    for candidate_id, expected in sorted(expected_by_candidate.items()):

        path = ANALYSIS_DIR / f"{candidate_id}_analysis.json"

        # A manifest entry without a saved analysis is reported, not silently
        # dropped, so the denominator stays honest.
        if not path.exists():
            skipped.append(candidate_id)
            continue

        analysis = ResumeAnalysis.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )

        rows.extend(score_candidate(analysis, expected))

    if not rows:
        raise FileNotFoundError(
            f"No saved analyses matched the manifest in {ANALYSIS_DIR}"
        )

    summary = summarise(rows)

    print(RULE)
    print("RESUME ANALYZER SCORECARD  (stage 2 vs manifest labels)")
    print(RULE)
    print(f"  candidates scored : {len(rows) // 7}")
    print(f"  judgements        : {summary['judgements']}")
    print(f"  accuracy          : {summary['accuracy']:.3f}")
    print(f"  precision         : {summary['precision']:.3f}   (credited and truly evidenced)")
    print(f"  recall            : {summary['recall']:.3f}   (evidenced and found)")
    print()
    print(f"  correct evidence  : {summary['counts']['correct_evidence']}")
    print(f"  correct unknown   : {summary['counts']['correct_unknown']}")
    print(f"  OVER-credit       : {summary['counts']['over_credit']}   <- probes skipped")
    print(f"  under-credit      : {summary['counts']['under_credit']}   <- questions wasted")

    if skipped:
        print()
        print(f"  no saved analysis : {', '.join(skipped)}")

    over = [r for r in rows if r["outcome"] == "over_credit"]

    if over:
        print()
        print(RULE)
        print("OVER-CREDITED  (resume silent, analyzer claimed evidence)")
        print(RULE)
        print(f"{'CANDIDATE':<16}{'COMPETENCY':<30}{'LEVEL':<20}CONF")
        for row in over:
            print(
                f"{row['candidate_id']:<16}{row['competency']:<30}"
                f"{row['actual_level']:<20}{row['confidence']:.2f}"
            )

    under = [r for r in rows if r["outcome"] == "under_credit"]

    if under:
        print()
        print(RULE)
        print("UNDER-CREDITED  (resume showed evidence, analyzer said unknown)")
        print(RULE)
        print(f"{'CANDIDATE':<16}{'COMPETENCY':<30}{'PROBE':<8}CONF")
        for row in under:
            print(
                f"{row['candidate_id']:<16}{row['competency']:<30}"
                f"{row['probe_priority']:<8}{row['confidence']:.2f}"
            )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps({"summary": summary, "judgements": rows}, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"saved: {REPORT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
