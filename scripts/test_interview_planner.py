import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.test_interview_planner.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.resume_analysis import ResumeAnalysis
from src.planning.interview_planner import create_interview_plan


INPUT_FILE = PROJECT_ROOT / (
    "data/prepared/resume_analysis/candidate_10_analysis.json"
)

OUTPUT_DIR = PROJECT_ROOT / (
    "data/prepared/interview_plans"
)


def main():

    print(f"Loading: {INPUT_FILE}")

    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    resume_analysis = ResumeAnalysis.model_validate(data)

    print(f"Candidate: {resume_analysis.candidate_id}")
    print("Creating interview plan...\n")

    plan = create_interview_plan(resume_analysis)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR /
        f"{resume_analysis.candidate_id}_plan.json"
    )

    output_file.write_text(
        plan.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print("=" * 70)
    print("INTERVIEW PLAN")
    print("=" * 70)

    print(f"\nCandidate       : {plan.candidate_id}")
    print(f"Total Questions : {plan.total_questions}")

    print("\nCOMPETENCY ALLOCATION")
    print("-" * 70)

    for target in plan.competency_targets:

        print(
            f"\n{target.competency.value}"
        )

        print(
            f"  Questions : {target.question_count}"
        )

        print(
            f"  Reason    : {target.reason}"
        )

    difficulty = plan.difficulty_distribution

    print("\nDIFFICULTY DISTRIBUTION")
    print("-" * 70)

    print(f"Basic        : {difficulty.basic}")
    print(f"Intermediate : {difficulty.intermediate}")
    print(f"Advanced     : {difficulty.advanced}")

    print("\nSTRATEGY")
    print("-" * 70)

    print(
        f"Validate strengths : "
        f"{plan.strategy.validate_claimed_strengths}"
    )

    print(
        f"Probe unknowns     : "
        f"{plan.strategy.probe_unknown_areas}"
    )

    print(
        f"Avoid assumptions  : "
        f"{plan.strategy.avoid_resume_based_negative_assumptions}"
    )

    print(
        f"Rationale          : "
        f"{plan.strategy.rationale}"
    )

    print("\n" + "=" * 70)

    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
