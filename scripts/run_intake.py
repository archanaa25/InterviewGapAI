"""
Run the InterviewGapAI intake pipeline on one resume.

    resume file -> CandidateResume -> ResumeAnalysis -> InterviewPlan
                -> InterviewQuestionSet (handed to the Interview Agent)

Each stage writes a JSON artifact and reuses one that already exists, so a
failed or slow stage can be retried without repaying for the stages before
it. Pass --force to recompute.

Usage:
    uv run python scripts/run_intake.py data/synthetic/resumes/candidate_01.md
    uv run python scripts/run_intake.py my_resume.md --candidate-id archana
    uv run python scripts/run_intake.py resume.md --stop-after plan --force
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.interview.question_selector import select_interview_questions
from src.planning.interview_planner import create_interview_plan
from src.resume.analyzer import analyze_resume
from src.resume.extractor import extract_resume
from src.schemas.interview_plan import InterviewPlan
from src.schemas.interview_questions import InterviewQuestionSet
from src.schemas.resume import CandidateResume
from src.schemas.resume_analysis import ResumeAnalysis


STAGES = ("extract", "analyze", "plan", "questions")

TEXT_SUFFIXES = {".md", ".markdown", ".txt"}

RULE = "=" * 72


def display_path(path: Path) -> str:
    """Show a project-relative path when possible, else the full path."""

    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        # --out-dir can point outside the repository, for example a scratch
        # directory used while testing.
        return str(path)


def parse_args():

    parser = argparse.ArgumentParser(
        description="Run the intake pipeline on one resume.",
    )

    parser.add_argument(
        "resume",
        type=Path,
        help="Resume file (.md or .txt).",
    )

    parser.add_argument(
        "--candidate-id",
        help="Identifier for artifacts. Defaults to the filename stem.",
    )

    parser.add_argument(
        "--stop-after",
        choices=STAGES,
        default="questions",
        help="Last stage to run. Default: questions.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute stages even when an artifact already exists.",
    )

    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "prepared",
        help="Root directory for artifacts. Default: data/prepared.",
    )

    return parser.parse_args()


def read_resume_text(path: Path) -> str:
    """Read a resume file, refusing formats the extractor cannot handle."""

    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")

    suffix = path.suffix.lower()

    # Binary formats need a text-extraction dependency this project does not
    # install. Fail with the conversion command rather than feeding the model
    # unreadable bytes.
    if suffix not in TEXT_SUFFIXES:
        raise ValueError(
            f"Unsupported resume format '{suffix}'. Supported: "
            f"{', '.join(sorted(TEXT_SUFFIXES))}.\n"
            f"Convert first, for example:\n"
            f"    pdftotext -layout '{path}' resume.txt"
        )

    text = path.read_text(encoding="utf-8").strip()

    if not text:
        raise ValueError(f"Resume file is empty: {path}")

    return text


def load_or_build(path: Path, model, build, force: bool, label: str):
    """Return a cached artifact when present, otherwise build and save it."""

    if path.exists() and not force:
        print(f"  {label:<22} cached   {display_path(path)}")
        return model.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        ), True

    print(f"  {label:<22} running...")

    artifact = build()

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print(f"  {label:<22} saved    {display_path(path)}")

    return artifact, False


def print_analysis(analysis: ResumeAnalysis):

    print()
    print(RULE)
    print("RESUME ANALYSIS")
    print(RULE)
    print(analysis.overall_summary)
    print()

    print(f"{'COMPETENCY':<30}{'EVIDENCE':<24}{'PROBE':<8}CONF")

    for item in analysis.competency_evidence:
        print(
            f"{item.competency.value:<30}"
            f"{item.evidence_level.value:<24}"
            f"{item.probe_priority.value:<8}"
            f"{item.confidence:.2f}"
        )


def print_plan(plan: InterviewPlan):

    print()
    print(RULE)
    print("INTERVIEW PLAN")
    print(RULE)

    print(f"{'COMPETENCY':<30}{'BAS':>5}{'INT':>5}{'ADV':>5}{'TOTAL':>7}")

    for target in plan.competency_targets:
        print(
            f"{target.competency.value:<30}"
            f"{target.basic:>5}{target.intermediate:>5}"
            f"{target.advanced:>5}{target.question_count:>7}"
        )

    distribution = plan.difficulty_distribution

    print(
        f"{'':<30}{distribution.basic:>5}"
        f"{distribution.intermediate:>5}"
        f"{distribution.advanced:>5}"
        f"{plan.total_questions:>7}"
    )

    print()
    print("Strategy:")
    print(f"  {plan.strategy.rationale}")


def print_questions(question_set: InterviewQuestionSet):

    print()
    print(RULE)
    print("INTERVIEW QUESTIONS  (handed to the Interview Agent)")
    print(RULE)

    for question in question_set.questions:

        relaxed = (
            "  [difficulty relaxed]"
            if question.retrieval.filter_relaxed
            else ""
        )

        print()
        print(
            f"{question.position:>2}. {question.question_id} "
            f"({question.competency.value} / {question.difficulty})"
            f"{relaxed}"
        )
        print(f"    {question.question}")
        print(
            f"    grades on: "
            f"{'; '.join(question.expected_concepts.must_have)}"
        )

    for slot in question_set.unfilled_slots:
        print()
        print(f"UNFILLED: {slot.reason}")

    for warning in question_set.warnings:
        print()
        print(f"WARNING: {warning}")


def main():

    args = parse_args()

    resume_path = args.resume
    candidate_id = args.candidate_id or resume_path.stem

    resume_text = read_resume_text(resume_path)

    out_dir = args.out_dir

    paths = {
        "extract": out_dir / "resumes" / f"{candidate_id}.json",
        "analyze": out_dir / "resume_analysis" / f"{candidate_id}_analysis.json",
        "plan": out_dir / "interview_plans" / f"{candidate_id}_plan.json",
        "questions": out_dir / "interview_questions" / f"{candidate_id}_questions.json",
    }

    stop_index = STAGES.index(args.stop_after)

    print(RULE)
    print("INTAKE PIPELINE")
    print(RULE)
    print(f"  {'resume':<22} {resume_path}")
    print(f"  {'candidate_id':<22} {candidate_id}")
    print(f"  {'characters':<22} {len(resume_text)}")
    print(f"  {'stop after':<22} {args.stop_after}")
    print()

    resume, _ = load_or_build(
        paths["extract"],
        CandidateResume,
        lambda: extract_resume(
            resume_text=resume_text,
            candidate_id=candidate_id,
        ),
        args.force,
        "1 extract resume",
    )

    print(f"     name={resume.name!r} target_role={resume.target_role!r} "
          f"skills={len(resume.skills)}")

    if stop_index < STAGES.index("analyze"):
        return

    analysis, _ = load_or_build(
        paths["analyze"],
        ResumeAnalysis,
        lambda: analyze_resume(resume),
        args.force,
        "2 analyze evidence",
    )

    print_analysis(analysis)

    if stop_index < STAGES.index("plan"):
        return

    print()

    plan, _ = load_or_build(
        paths["plan"],
        InterviewPlan,
        lambda: create_interview_plan(analysis),
        args.force,
        "3 build plan",
    )

    print_plan(plan)

    if stop_index < STAGES.index("questions"):
        return

    print()

    question_set, _ = load_or_build(
        paths["questions"],
        InterviewQuestionSet,
        lambda: select_interview_questions(plan),
        args.force,
        "4 select questions",
    )

    print_questions(question_set)

    print()
    print(RULE)
    print(
        f"Ready for the Interview Agent: "
        f"{len(question_set.questions)} questions, "
        f"complete={question_set.is_complete}"
    )
    print(RULE)


if __name__ == "__main__":
    main()
