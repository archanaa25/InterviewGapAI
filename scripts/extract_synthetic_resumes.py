import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Direct script execution puts scripts/, rather than the project root, on sys.path.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.resume.extractor import extract_resume_file


INPUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "resumes"
OUTPUT_DIR = PROJECT_ROOT / "data" / "prepared" / "resumes"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    resume_files = sorted(INPUT_DIR.glob("candidate_*.md"))

    if not resume_files:
        raise FileNotFoundError(
            f"No candidate resumes found in {INPUT_DIR}"
        )

    print(f"Found {len(resume_files)} resumes\n")

    success_count = 0
    failure_count = 0

    for resume_path in resume_files:
        print(f"Processing: {resume_path.name}")

        try:
            resume = extract_resume_file(resume_path)

            output_path = OUTPUT_DIR / f"{resume_path.stem}.json"

            output_path.write_text(
                json.dumps(
                    resume.model_dump(),
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            print(f"  ✓ Created {output_path}")

            success_count += 1

        except Exception as exc:
            print(f"  ✗ FAILED: {exc}")
            failure_count += 1

    print("\n" + "=" * 60)
    print("RESUME EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total   : {len(resume_files)}")
    print(f"Success : {success_count}")
    print(f"Failed  : {failure_count}")


if __name__ == "__main__":
    main()
