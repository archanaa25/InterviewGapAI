import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.validate_resume_analyses.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.schemas.resume_analysis import ResumeAnalysis, Competency


INPUT_DIR = PROJECT_ROOT / "data/prepared/resume_analysis"

EXPECTED_COMPETENCIES = {c.value for c in Competency}


def short_level(level):
    mapping = {
        "DEMONSTRATED": "DEM",
        "PARTIAL_EVIDENCE": "PARTIAL",
        "UNKNOWN_NEEDS_PROBING": "UNKNOWN",
    }
    return mapping.get(level, level)


def main():
    files = sorted(INPUT_DIR.glob("candidate_*_analysis.json"))

    if not files:
        raise FileNotFoundError(
            f"No resume analysis files found in {INPUT_DIR}"
        )

    rows = []

    valid_count = 0
    invalid_count = 0

    print(f"Found {len(files)} resume analyses\n")

    for file in files:
        try:
            data = json.loads(
                file.read_text(encoding="utf-8")
            )

            # Pydantic validation
            analysis = ResumeAnalysis.model_validate(data)

            competencies = [
                item.competency.value
                for item in analysis.competency_evidence
            ]

            competency_set = set(competencies)

            missing = EXPECTED_COMPETENCIES - competency_set

            duplicates = {
                c
                for c in competencies
                if competencies.count(c) > 1
            }

            if missing or duplicates:
                print(f"✗ {analysis.candidate_id}")

                if missing:
                    print(
                        f"  Missing competencies: "
                        f"{sorted(missing)}"
                    )

                if duplicates:
                    print(
                        f"  Duplicate competencies: "
                        f"{sorted(duplicates)}"
                    )

                invalid_count += 1
                continue

            if len(competencies) != 7:
                print(
                    f"✗ {analysis.candidate_id}: "
                    f"Expected 7 competencies, "
                    f"found {len(competencies)}"
                )

                invalid_count += 1
                continue

            # Convert to easy lookup
            evidence_map = {
                item.competency.value: item.evidence_level.value
                for item in analysis.competency_evidence
            }

            rows.append(
                {
                    "candidate": analysis.candidate_id,
                    "rag": short_level(
                        evidence_map["rag"]
                    ),
                    "agentic": short_level(
                        evidence_map["agentic_ai"]
                    ),
                    "fundamentals": short_level(
                        evidence_map["ai_ml_llm_fundamentals"]
                    ),
                    "evaluation": short_level(
                        evidence_map["ai_evaluation"]
                    ),
                    "software": short_level(
                        evidence_map["python_software_engineering"]
                    ),
                    "system_design": short_level(
                        evidence_map["ai_system_design"]
                    ),
                    "security": short_level(
                        evidence_map["ai_security"]
                    ),
                }
            )

            valid_count += 1

        except Exception as exc:
            print(f"✗ {file.name}: {exc}")
            invalid_count += 1

    print("\n" + "=" * 100)
    print("RESUME ANALYSIS VALIDATION")
    print("=" * 100)

    print(f"Files   : {len(files)}")
    print(f"Valid   : {valid_count}")
    print(f"Invalid : {invalid_count}")

    if rows:
        print("\n")

        header = (
            f"{'Candidate':<14}"
            f"{'RAG':<10}"
            f"{'Agentic':<10}"
            f"{'Fund':<10}"
            f"{'Eval':<10}"
            f"{'SWE':<10}"
            f"{'Design':<10}"
            f"{'Security':<10}"
        )

        print(header)
        print("-" * len(header))

        for row in rows:
            print(
                f"{row['candidate']:<14}"
                f"{row['rag']:<10}"
                f"{row['agentic']:<10}"
                f"{row['fundamentals']:<10}"
                f"{row['evaluation']:<10}"
                f"{row['software']:<10}"
                f"{row['system_design']:<10}"
                f"{row['security']:<10}"
            )


if __name__ == "__main__":
    main()
