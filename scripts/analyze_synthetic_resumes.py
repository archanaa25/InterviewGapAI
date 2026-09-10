import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.analyze_synthetic_resumes.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.resume import CandidateResume
from src.resume.analyzer import analyze_resume


INPUT_DIR = PROJECT_ROOT / "data/prepared/resumes"
OUTPUT_DIR = PROJECT_ROOT / "data/prepared/resume_analysis"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    resume_files = sorted(INPUT_DIR.glob("candidate_*.json"))

    if not resume_files:
        raise FileNotFoundError(
            f"No candidate resumes found in {INPUT_DIR}"
        )

    print(f"Found {len(resume_files)} resumes\n")

    success_count = 0
    failure_count = 0

    for resume_file in resume_files:
        candidate_id = resume_file.stem

        print(f"Processing: {candidate_id}")

        try:
            # Load structured resume
            resume_data = json.loads(
                resume_file.read_text(encoding="utf-8")
            )

            resume = CandidateResume.model_validate(resume_data)

            # Run Resume Analyzer
            analysis = analyze_resume(resume)

            # Save analysis
            output_file = (
                OUTPUT_DIR /
                f"{candidate_id}_analysis.json"
            )

            output_file.write_text(
                analysis.model_dump_json(indent=2),
                encoding="utf-8",
            )

            print(f"  ✓ Created {output_file}")

            # Quick sanity check
            competency_count = len(
                analysis.competency_evidence
            )

            print(
                f"  ✓ Competencies analyzed: "
                f"{competency_count}"
            )

            success_count += 1

        except Exception as exc:
            print(f"  ✗ FAILED: {exc}")
            failure_count += 1

        print()

    print("=" * 60)
    print("RESUME ANALYSIS SUMMARY")
    print("=" * 60)

    print(f"Total   : {len(resume_files)}")
    print(f"Success : {success_count}")
    print(f"Failed  : {failure_count}")


if __name__ == "__main__":
    main()
