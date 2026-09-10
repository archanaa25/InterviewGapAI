import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.create_interview_plans.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.resume_analysis import ResumeAnalysis
from src.planning.interview_planner import create_interview_plan


INPUT_DIR = PROJECT_ROOT / "data/prepared/resume_analysis"
OUTPUT_DIR = PROJECT_ROOT / "data/prepared/interview_plans"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        INPUT_DIR.glob("candidate_*_analysis.json")
    )

    if not files:
        raise FileNotFoundError(
            f"No resume analyses found in {INPUT_DIR}"
        )

    print(f"Found {len(files)} resume analyses\n")

    success = 0
    failed = 0

    for input_file in files:

        try:
            data = json.loads(
                input_file.read_text(encoding="utf-8")
            )

            analysis = ResumeAnalysis.model_validate(data)

            print(
                f"Planning interview: "
                f"{analysis.candidate_id}"
            )

            plan = create_interview_plan(analysis)

            output_file = (
                OUTPUT_DIR
                / f"{analysis.candidate_id}_plan.json"
            )

            output_file.write_text(
                plan.model_dump_json(indent=2),
                encoding="utf-8",
            )

            competency_total = sum(
                target.question_count
                for target in plan.competency_targets
            )

            difficulty_total = (
                plan.difficulty_distribution.basic
                + plan.difficulty_distribution.intermediate
                + plan.difficulty_distribution.advanced
            )

            print(
                f"  ✓ Questions: {competency_total}"
            )

            print(
                f"  ✓ Difficulty total: {difficulty_total}"
            )

            print(
                f"  ✓ Created: {output_file}"
            )

            success += 1

        except Exception as exc:

            print(
                f"  ✗ FAILED: {exc}"
            )

            failed += 1

        print()

    print("=" * 60)
    print("INTERVIEW PLANNING SUMMARY")
    print("=" * 60)

    print(f"Total   : {len(files)}")
    print(f"Success : {success}")
    print(f"Failed  : {failed}")


if __name__ == "__main__":
    main()
