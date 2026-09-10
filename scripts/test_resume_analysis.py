import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.test_resume_analysis.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.resume import CandidateResume
from src.resume.analyzer import analyze_resume


INPUT_FILE = PROJECT_ROOT / "data/prepared/resumes/candidate_10.json"

OUTPUT_DIR = PROJECT_ROOT / "data/prepared/resume_analysis"


def main():
    print(f"Loading: {INPUT_FILE}")

    resume_data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    resume = CandidateResume.model_validate(resume_data)

    print(f"Candidate: {resume.name}")
    print("Running resume analysis...\n")

    analysis = analyze_resume(resume)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "candidate_10_analysis.json"

    output_file.write_text(
        analysis.model_dump_json(indent=2),
        encoding="utf-8",
    )

    print("=" * 70)
    print("RESUME ANALYSIS")
    print("=" * 70)

    for item in analysis.competency_evidence:
        print(f"\nCompetency     : {item.competency.value}")
        print(f"Evidence Level : {item.evidence_level.value}")
        print(f"Probe Priority : {item.probe_priority.value}")
        print(f"Confidence     : {item.confidence}")
        print(f"Reason         : {item.reason}")

        if item.evidence:
            print("Evidence:")
            for evidence in item.evidence:
                print(f"  - {evidence.evidence}")
                print(f"    Source: {evidence.source}")
        else:
            print("Evidence       : None")

    print("\n" + "=" * 70)
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()
