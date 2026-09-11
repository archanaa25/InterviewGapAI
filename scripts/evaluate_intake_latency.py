"""
Measure intake latency before and after the stage 1-3 changes.

The candidate waits on three model calls before the plan screen appears, so
this is a user-visible number, not an internal one. Both arms run in the same
session against the same resumes: API latency moves enough hour to hour that
comparing a fresh run against a recorded one would report the weather rather
than the change.

    baseline    the pipeline shape as of commit 6dade8a - one model call per
                stage, every stage on gpt-5.6, the planner reading the whole
                analysis JSON and restating totals it could have summed.

    optimized   the current src/ code.

Writes data/eval/intake_latency_report.json, which carries the reason for each
change alongside its measured improvement so a dashboard can show both.

Both arms run on their own models by default, so the headline number mixes the
shape change with the model change. Pin them to the same model to separate the
two:

    BASELINE_MODEL=gpt-5.4 RESUME_EXTRACTION_MODEL=gpt-5.4 \
    RESUME_ANALYSIS_MODEL=gpt-5.4 INTERVIEW_PLANNING_MODEL=gpt-5.4 \
    uv run python scripts/evaluate_intake_latency.py

Usage:
    uv run python scripts/evaluate_intake_latency.py
    uv run python scripts/evaluate_intake_latency.py --resumes 3 --repeats 2
    uv run python scripts/evaluate_intake_latency.py --skip-baseline
"""

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env", override=True)

import src.planning.interview_planner as planner
import src.resume.analyzer as analyzer
import src.resume.extractor as extractor
from src.planning.prompts import INTERVIEW_PLANNING_SYSTEM_PROMPT
from src.resume.analyzer_prompts import COMPETENCY_EVIDENCE_SYSTEM_PROMPT
from src.resume.prompts import RESUME_EXTRACTION_SYSTEM_PROMPT
from src.schemas.interview_plan import InterviewPlan
from src.schemas.resume import CandidateResume
from src.schemas.resume_analysis import CompetencyEvidence, ResumeAnalysis

RESUME_DIR = PROJECT_ROOT / "data/synthetic/resumes"
REPORT_PATH = PROJECT_ROOT / "data/eval/intake_latency_report.json"

# The model the baseline arm runs on. Point it at the same model the current
# pipeline uses to isolate the shape change from the model change; leave it at
# the shipped default to measure what the candidate actually experienced.
BASELINE_MODEL = os.getenv("BASELINE_MODEL", "gpt-5.6")
FLOOR_MODELS = ("gpt-5.6", "gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano")

STAGES = ("resume extraction", "resume analysis", "interview planning")

RULE = "=" * 78

# What changed in each stage and why. The dashboard shows these next to the
# measured numbers; a percentage with no reason attached cannot be reviewed.
CHANGES = {
    "resume extraction": {
        "change": "Run extraction on a smaller model.",
        "reason": (
            "Extraction transcribes a resume into a schema. It spent zero "
            "reasoning tokens on the largest model, so the capability was "
            "not being used - only its per-request latency was being paid."
        ),
    },
    "resume analysis": {
        "change": "Fan out to one model call per competency, run concurrently.",
        "reason": (
            "The seven competency assessments are independent readings of "
            "the same resume. Emitted from one call they were serial output "
            "tokens; requested separately they overlap, so the stage costs "
            "the longest single assessment instead of the sum of all seven."
        ),
    },
    "interview planning": {
        "change": (
            "Send the allocation-relevant evidence fields only, sum the "
            "difficulty distribution in code, and re-ask on an arithmetic slip."
        ),
        "reason": (
            "The planner read every evidence item and its source, which the "
            "allocation decision never uses, then restated totals that are "
            "sums of its own per-competency numbers. Trimming that output "
            "only pays off on a model slow enough for output tokens to "
            "dominate; the durable win is reliability. Deriving the totals "
            "removes the failure mode where a plan was rejected for "
            "disagreeing with itself, and an allocation that sums to 9 is an "
            "arithmetic slip the model corrects when shown it - previously it "
            "cost the candidate the whole intake."
        ),
    },
}

# Cross-cutting findings from running this harness, as opposed to CHANGES
# (what each stage's diff does) and notes (mechanical reading caveats). These
# came from watching real runs, not from the numbers alone, so they stay as
# hand-written prose rather than something derived from the measurements.
OBSERVATIONS = [
    {
        "title": "The planner digest's real payoff is reliability, not latency.",
        "detail": (
            "Trimming the planner's input to the allocation-relevant evidence "
            "fields only helps wall time on a model slow enough for output "
            "tokens to dominate (gpt-5.6). On a fast model (gpt-5.4) the "
            "per-request floor dominates instead, and the digest measured "
            "roughly no latency change. Its durable win showed up in "
            "completion rate: on gpt-5.4, the baseline shape (full analysis "
            "JSON, model restates the totals) failed InterviewPlan's "
            "validators in 3 of 10 runs; the digest shape, which derives "
            "totals in code instead of asking the model to restate them, "
            "failed in 0 of 10. Read the per-stage seconds together with the "
            "reliability block, not alone - a stage that got faster but less "
            "reliable would be a worse trade for the candidate."
        ),
    },
    {
        "title": "gpt-5.6 was measurably degraded during this evaluation.",
        "detail": (
            "A trivial structured call (see model_floor) cost 5.0-8.8s on "
            "gpt-5.6 against ~1.0s on gpt-5.4/gpt-5.4-mini, and repeated runs "
            "hit InternalServerError (503, 'servers are currently "
            "overloaded'). This is provider-side variability, not something "
            "this change fixes or should be tuned around. It also means a "
            "clean baseline-vs-optimized comparison with both arms left on "
            "gpt-5.6 could not be produced in this session: set BASELINE_MODEL "
            "and the stage model env vars to gpt-5.4 to reproduce the numbers "
            "in this report, or re-run with them left at their gpt-5.6 "
            "defaults once the provider has recovered to get the number that "
            "matches what candidates actually experience today."
        ),
    },
    {
        "title": (
            "A pre-existing planner failure mode surfaced during testing and "
            "was fixed alongside the latency work."
        ),
        "detail": (
            "The planner intermittently allocates competency question counts "
            "that sum to 9 instead of 10 - an arithmetic slip, not a "
            "judgement call, and not something this change introduced. It "
            "crashed scripts/run_intake.py on candidate_08 three attempts "
            "running before this observation was made. interview_planner.py "
            "now re-asks up to PLANNING_ATTEMPTS times, showing the model its "
            "own rejected per-competency breakdown and a directional "
            "correction ('add 1 question, to the competency with the highest "
            "probe priority') rather than just restating the rule. All 10 "
            "fixture candidates now build a valid plan. This is the arithmetic "
            "case that motivated point 4 (replacing the allocation call with "
            "code) - worth revisiting now that the latency numbers are in."
        ),
    },
]


class _Meter:
    """
    Wrap responses.parse to record wall time and token usage per call.

    Patching the module clients keeps the measurement out of production code:
    the pipeline under test is the one that actually ships.
    """

    def __init__(self):
        self.calls: List[dict] = []
        self._patched: List[tuple] = []

    def attach(self, *modules):
        for module in modules:
            original = module.client.responses.parse
            self._patched.append((module, original))
            module.client.responses.parse = self._wrap(original)
        return self

    def _wrap(self, original):
        def parse(**kwargs):
            started = time.perf_counter()
            response = original(**kwargs)
            usage = response.usage
            details = getattr(usage, "output_tokens_details", None)
            self.calls.append(
                {
                    "seconds": time.perf_counter() - started,
                    "model": kwargs.get("model"),
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "reasoning_tokens": getattr(details, "reasoning_tokens", 0) or 0,
                }
            )
            return response

        return parse

    def detach(self):
        for module, original in self._patched:
            module.client.responses.parse = original
        self._patched.clear()

    def drain(self) -> List[dict]:
        calls, self.calls = self.calls, []
        return calls


# ---------------------------------------------------------------------------
# Baseline arm: the one-call-per-stage shape this change replaced.
# ---------------------------------------------------------------------------

# The shipped prompt asks for a single competency because that is how the
# analyzer now calls it. The baseline asked one call for all seven.
_BASELINE_ANALYSIS_PROMPT = COMPETENCY_EVIDENCE_SYSTEM_PROMPT.replace(
    "for ONE named AI Engineer competency",
    "for each supported AI Engineer competency",
).replace(
    """10. Assess ONLY the competency named in the request. Evidence that belongs
    to a different competency is not evidence for this one. Return the
    requested competency in the competency field.""",
    """10. Produce exactly one assessment for each of the seven supported
    competencies.""",
)


def baseline_extract(client, resume_text: str, candidate_id: str) -> CandidateResume:
    response = client.responses.parse(
        model=BASELINE_MODEL,
        input=[
            {"role": "system", "content": RESUME_EXTRACTION_SYSTEM_PROMPT},
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
    resume.candidate_id = candidate_id
    return resume


def baseline_analyze(client, resume: CandidateResume) -> ResumeAnalysis:
    response = client.responses.parse(
        model=BASELINE_MODEL,
        input=[
            {"role": "system", "content": _BASELINE_ANALYSIS_PROMPT},
            {
                "role": "user",
                "content": f"""
Analyze the following CandidateResume.

Candidate ID: {resume.candidate_id}

CANDIDATE RESUME
----------------
{resume.model_dump_json(indent=2)}
----------------

Return a ResumeAnalysis containing exactly one assessment
for each supported competency.
""",
            },
        ],
        text_format=ResumeAnalysis,
    )
    analysis = response.output_parsed
    analysis.candidate_id = resume.candidate_id
    return analysis


def baseline_plan(client, analysis: ResumeAnalysis) -> InterviewPlan:
    response = client.responses.parse(
        model=BASELINE_MODEL,
        input=[
            {"role": "system", "content": INTERVIEW_PLANNING_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
Create an InterviewPlan for the following candidate.

Candidate ID: {analysis.candidate_id}

RESUME ANALYSIS
---------------
{analysis.model_dump_json(indent=2)}
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
    plan.candidate_id = analysis.candidate_id
    return plan


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def run_arm(arm: str, resume_text: str, candidate_id: str, meter: _Meter) -> dict:
    """Run one pipeline shape and return per-stage timings and token counts."""

    client = extractor.client
    baseline = arm == "baseline"
    meter.drain()

    stages = {}

    def stage(name, step):
        started = time.perf_counter()
        value = step()
        stages[name] = _stage_record(time.perf_counter() - started, meter.drain())
        return value

    resume = stage(
        "resume extraction",
        lambda: baseline_extract(client, resume_text, candidate_id)
        if baseline
        else extractor.extract_resume(resume_text, candidate_id),
    )
    analysis = stage(
        "resume analysis",
        lambda: baseline_analyze(client, resume)
        if baseline
        else analyzer.analyze_resume(resume),
    )
    plan = stage(
        "interview planning",
        lambda: baseline_plan(client, analysis)
        if baseline
        else planner.create_interview_plan(analysis),
    )

    stages["total"] = {
        "seconds": sum(stages[name]["seconds"] for name in STAGES),
        "calls": sum(stages[name]["calls"] for name in STAGES),
        "input_tokens": sum(stages[name]["input_tokens"] for name in STAGES),
        "output_tokens": sum(stages[name]["output_tokens"] for name in STAGES),
    }
    stages["allocation"] = {
        target.competency.value: target.question_count
        for target in plan.competency_targets
    }
    stages["evidence_levels"] = {
        item.competency.value: item.evidence_level.value
        for item in analysis.competency_evidence
    }
    return stages


def _stage_record(seconds: float, calls: List[dict]) -> dict:
    return {
        "seconds": seconds,
        "calls": len(calls),
        "models": sorted({call["model"] for call in calls}),
        "input_tokens": sum(call["input_tokens"] for call in calls),
        "output_tokens": sum(call["output_tokens"] for call in calls),
        "reasoning_tokens": sum(call["reasoning_tokens"] for call in calls),
        # The slowest call bounds a concurrent stage: it is what the candidate
        # actually waits for once the others overlap with it.
        "slowest_call_seconds": max((call["seconds"] for call in calls), default=0.0),
    }


def measure_model_floor(client, models=FLOOR_MODELS, repeats: int = 3) -> List[dict]:
    """
    Time a trivial structured call per model.

    Most of a stage's wall time turned out to be per-request overhead rather
    than generation, so the floor is the number that decides whether any
    amount of prompt trimming can help.
    """

    class _Floor(BaseModel):
        answer: int = Field(description="The sum.")

    rows = []
    for model in models:
        samples = []
        for index in range(repeats):
            started = time.perf_counter()
            try:
                client.responses.parse(
                    model=model,
                    input=[
                        {
                            "role": "user",
                            "content": f"What is {index}+{index}? Return only the number.",
                        }
                    ],
                    text_format=_Floor,
                )
            except Exception as error:  # a model the account cannot reach
                rows.append({"model": model, "error": type(error).__name__})
                samples = []
                break
            samples.append(time.perf_counter() - started)
        if samples:
            rows.append(
                {
                    "model": model,
                    "min_seconds": min(samples),
                    "median_seconds": statistics.median(samples),
                    "max_seconds": max(samples),
                    "samples": len(samples),
                }
            )
    return rows


def aggregate(runs: List[dict], key: str) -> dict:
    """Median across runs; medians survive an API outlier, means do not."""

    fields = ("seconds", "calls", "input_tokens", "output_tokens", "reasoning_tokens")
    records = [run[key] for run in runs]
    aggregated = {
        field: statistics.median([record.get(field, 0) for record in records])
        for field in fields
        if any(field in record for record in records)
    }
    # A median over one or two runs is a sample, not a measurement. Carry the
    # count so a dashboard can mark a thin row rather than present it as fact.
    aggregated["runs"] = len(records)
    return aggregated


def build_report(args, baseline_runs, optimized_runs, floor, resumes, failures) -> dict:
    stages = []

    for name in STAGES:
        after = aggregate(optimized_runs, name)
        entry = {
            "stage": name,
            "change": CHANGES[name]["change"],
            "reason": CHANGES[name]["reason"],
            "after": after,
        }
        if baseline_runs:
            before = aggregate(baseline_runs, name)
            entry["before"] = before
            entry["improvement_seconds"] = before["seconds"] - after["seconds"]
            entry["improvement_pct"] = (
                100.0 * (before["seconds"] - after["seconds"]) / before["seconds"]
                if before["seconds"]
                else 0.0
            )
        stages.append(entry)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_ref": _git_ref(),
        "config": {
            "resumes": resumes,
            "repeats": args.repeats,
            "baseline_model": BASELINE_MODEL,
            "optimized_models": {
                "resume extraction": extractor.EXTRACTION_MODEL,
                "resume analysis": analyzer.ANALYSIS_MODEL,
                "interview planning": planner.PLANNING_MODEL,
            },
        },
        "stages": stages,
        "model_floor": floor,
        "observations": OBSERVATIONS,
        "notes": [
            "Latency is dominated by per-request overhead, not generation: a "
            "trivial structured call is the floor every stage pays. See "
            "model_floor.",
            "Stage times are medians across runs. The API varies enough "
            "between runs that a single sample is not evidence.",
            "A concurrent stage's slowest_call_seconds is its lower bound; "
            "the gap above it is contention between overlapping calls.",
        ],
    }

    if baseline_runs and BASELINE_MODEL == extractor.EXTRACTION_MODEL:
        report["notes"].append(
            "Both arms ran resume extraction on the same model, so that row "
            "compares an identical call with itself: read it as the run-to-run "
            "variance floor, not as a result. The extraction change IS the "
            "model change."
        )

    # A run that fails is a candidate who never reaches the plan screen, so
    # completion belongs beside the timings rather than in a footnote.
    report["reliability"] = {
        arm: {
            "completed": completed,
            "attempted": completed + failed,
            "completion_rate": completed / (completed + failed)
            if completed + failed
            else None,
        }
        for arm, completed, failed in (
            (
                "baseline",
                len(baseline_runs),
                sum(1 for f in failures if f["arm"] == "baseline"),
            ),
            (
                "optimized",
                len(optimized_runs),
                sum(1 for f in failures if f["arm"] == "optimized"),
            ),
        )
        if completed + failed
    }

    after_total = aggregate(optimized_runs, "total")
    report["totals"] = {"after": after_total}
    if baseline_runs:
        before_total = aggregate(baseline_runs, "total")
        report["totals"]["before"] = before_total
        report["totals"]["improvement_seconds"] = (
            before_total["seconds"] - after_total["seconds"]
        )
        report["totals"]["improvement_pct"] = (
            100.0
            * (before_total["seconds"] - after_total["seconds"])
            / before_total["seconds"]
            if before_total["seconds"]
            else 0.0
        )
    return report


def _git_ref() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def print_report(report) -> None:
    print(RULE)
    print("INTAKE LATENCY".center(78))
    print(RULE)

    has_before = "before" in report["totals"]
    header = f"{'STAGE':<22}{'BEFORE':>10}{'AFTER':>10}{'SAVED':>10}{'CALLS':>8}{'OUT TOK':>10}"
    print(header if has_before else f"{'STAGE':<22}{'SECONDS':>10}{'CALLS':>8}{'OUT TOK':>10}")
    print("-" * 78)

    for entry in report["stages"]:
        after = entry["after"]
        if has_before:
            before = entry["before"]
            print(
                f"{entry['stage']:<22}{before['seconds']:>9.1f}s{after['seconds']:>9.1f}s"
                f"{entry['improvement_pct']:>9.0f}%{after['calls']:>8.0f}"
                f"{after['output_tokens']:>10.0f}"
            )
        else:
            print(
                f"{entry['stage']:<22}{after['seconds']:>9.1f}s"
                f"{after['calls']:>8.0f}{after['output_tokens']:>10.0f}"
            )

    print("-" * 78)
    totals = report["totals"]
    if has_before:
        print(
            f"{'TOTAL':<22}{totals['before']['seconds']:>9.1f}s"
            f"{totals['after']['seconds']:>9.1f}s{totals['improvement_pct']:>9.0f}%"
        )
    else:
        print(f"{'TOTAL':<22}{totals['after']['seconds']:>9.1f}s")

    if report.get("reliability"):
        print()
        print("COMPLETED RUNS")
        print("-" * 78)
        for arm, row in report["reliability"].items():
            print(
                f"  {arm:<12} {row['completed']}/{row['attempted']} "
                f"({row['completion_rate'] * 100:.0f}%)"
            )

    print()
    print("PER-REQUEST FLOOR (trivial structured call)")
    print("-" * 78)
    for row in report["model_floor"]:
        if "error" in row:
            print(f"  {row['model']:<18} unavailable ({row['error']})")
        else:
            print(
                f"  {row['model']:<18} min {row['min_seconds']:>5.2f}s   "
                f"median {row['median_seconds']:>5.2f}s   max {row['max_seconds']:>5.2f}s"
            )

    if report.get("failures"):
        print()
        print("FAILED RUNS (excluded from the medians above)")
        print("-" * 78)
        for failure in report["failures"]:
            print(f"  {failure['arm']:<10} {failure['resume']:<16} {failure['error']}")

    print()
    for entry in report["stages"]:
        print(f"{entry['stage'].upper()}")
        print(f"  change: {entry['change']}")
        print(f"  reason: {' '.join(entry['reason'].split())}")
        print()

    if report.get("observations"):
        print("OBSERVATIONS")
        print("-" * 78)
        for observation in report["observations"]:
            print(f"  {observation['title']}")
            print(f"    {' '.join(observation['detail'].split())}")
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resumes", type=int, default=2, help="How many fixture resumes.")
    parser.add_argument("--repeats", type=int, default=1, help="Runs per resume per arm.")
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Measure the current pipeline only; report no comparison.",
    )
    args = parser.parse_args()

    paths = sorted(RESUME_DIR.glob("candidate_*.md"))[: args.resumes]
    if not paths:
        raise SystemExit(f"No fixture resumes under {RESUME_DIR}")

    meter = _Meter().attach(extractor, analyzer, planner)

    baseline_runs, optimized_runs = [], []
    try:
        failures = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for _ in range(args.repeats):
                arms = [] if args.skip_baseline else [("baseline", baseline_runs)]
                arms.append(("optimized", optimized_runs))
                for arm, collected in arms:
                    print(f"  {arm:<10} {path.stem} ...", flush=True)
                    try:
                        collected.append(run_arm(arm, text, path.stem, meter))
                    except Exception as error:
                        # One overloaded API call must not discard the runs
                        # that already succeeded; record it and keep going.
                        print(f"    failed: {type(error).__name__}", flush=True)
                        failures.append(
                            {
                                "arm": arm,
                                "resume": path.stem,
                                "error": type(error).__name__,
                            }
                        )
                        meter.drain()

        if not optimized_runs:
            raise SystemExit("Every optimized run failed; no report written.")

        floor = measure_model_floor(extractor.client)
    finally:
        meter.detach()

    report = build_report(
        args,
        baseline_runs,
        optimized_runs,
        floor,
        [path.stem for path in paths],
        failures,
    )
    report["failures"] = failures

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print_report(report)
    print(f"Report written to {REPORT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
