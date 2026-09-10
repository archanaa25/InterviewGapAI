import json
import re
from collections import defaultdict
from pathlib import Path


QUESTIONS_FILE = Path(
    "data/prepared/master/interview_questions.jsonl"
)

EVALUATION_FILE = Path(
    "data/prepared/master/evaluation_knowledge.jsonl"
)


def load_jsonl(path):
    records = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records


def normalize(text):
    """
    Normalize text for lightweight lexical comparison.
    """
    text = str(text).lower()

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(text):
    """
    Convert normalized text into useful lexical tokens.
    """
    stop_words = {
        "the", "a", "an", "and", "or", "to", "of",
        "in", "on", "for", "with", "is", "are", "be",
        "can", "should", "from", "by", "as", "that",
        "this", "when", "while", "into",
    }

    return {
        token
        for token in normalize(text).split()
        if token not in stop_words and len(token) > 2
    }


def concept_similarity(concept, evaluation_text):
    """
    Lightweight lexical coverage score.

    This is intentionally NOT treated as final semantic evaluation.
    It is used to identify concepts that need further review.
    """

    concept_tokens = tokenize(concept)
    evaluation_tokens = tokenize(evaluation_text)

    if not concept_tokens:
        return 0.0

    overlap = concept_tokens & evaluation_tokens

    return len(overlap) / len(concept_tokens)


def get_question_concepts(question):
    """
    Extract expected concepts from the interview question schema.

    Schema:
        expected_concepts:
            must_have: [...]
            bonus: [...]
    """

    expected = question.get("expected_concepts", {}) or {}

    must_have = expected.get("must_have", []) or []
    bonus = expected.get("bonus", []) or []

    return must_have, bonus

# def get_question_concepts(question):
#     """
#     Support the concept representation used by the question corpus.

#     Adjust here if your corpus uses a slightly different structure.
#     """

#     must_have = question.get("must_have_concepts", [])
#     bonus = question.get("bonus_concepts", [])

#     # Defensive handling in case values are null.
#     must_have = must_have or []
#     bonus = bonus or []

#     return must_have, bonus


def build_evaluation_text(records):
    """
    Combine the referenced evaluation knowledge into one searchable
    text representation.
    """

    parts = []

    for record in records:

        parts.append(record.get("topic", ""))
        parts.append(record.get("content", ""))

        parts.extend(
            record.get("key_concepts", []) or []
        )

        parts.extend(
            record.get("common_misconceptions", []) or []
        )

        parts.extend(
            record.get("tags", []) or []
        )

    return " ".join(str(part) for part in parts)


def main():

    questions = load_jsonl(QUESTIONS_FILE)
    evaluations = load_jsonl(EVALUATION_FILE)

    eval_by_id = {
        record["evaluation_id"]: record
        for record in evaluations
    }

    total_must = 0
    covered_must = 0

    total_bonus = 0
    covered_bonus = 0

    empty_must_questions = []

    weak_questions = []

    missing_refs = []

    competency_stats = defaultdict(
        lambda: {
            "must_total": 0,
            "must_covered": 0,
        }
    )

    # Diagnostic threshold only.
    #
    # >= 0.60 means enough important words overlap that the concept
    # is provisionally considered lexically covered.
    #
    # Anything below this will be reviewed later semantically.
    threshold = 0.60

    for question in questions:

        question_id = question["question_id"]
        competency = question["competency"]

        refs = question.get("evaluation_refs", []) or []

        referenced_records = []

        invalid_refs = []

        for ref in refs:

            if ref in eval_by_id:
                referenced_records.append(
                    eval_by_id[ref]
                )
            else:
                invalid_refs.append(ref)

        if invalid_refs:

            missing_refs.append(
                {
                    "question_id": question_id,
                    "refs": invalid_refs,
                }
            )

        evaluation_text = build_evaluation_text(
            referenced_records
        )

        must_have, bonus = get_question_concepts(
            question
        )

        if not must_have:
            empty_must_questions.append(
                {
                    "question_id": question_id,
                    "competency": competency,
                    "question": question.get(
                        "question",
                        "",
                    ),
                    "evaluation_refs": refs,
                }
            )

        question_weak_concepts = []

        # ----------------------------------------
        # Must-have concepts
        # ----------------------------------------

        for concept in must_have:

            total_must += 1

            competency_stats[
                competency
            ]["must_total"] += 1

            score = concept_similarity(
                concept,
                evaluation_text,
            )

            if score >= threshold:

                covered_must += 1

                competency_stats[
                    competency
                ]["must_covered"] += 1

            else:

                question_weak_concepts.append(
                    {
                        "type": "must_have",
                        "concept": concept,
                        "lexical_score": round(
                            score,
                            3,
                        ),
                    }
                )

        # ----------------------------------------
        # Bonus concepts
        # ----------------------------------------

        for concept in bonus:

            total_bonus += 1

            score = concept_similarity(
                concept,
                evaluation_text,
            )

            if score >= threshold:
                covered_bonus += 1
            else:
                question_weak_concepts.append(
                    {
                        "type": "bonus",
                        "concept": concept,
                        "lexical_score": round(
                            score,
                            3,
                        ),
                    }
                )

        if question_weak_concepts:

            weak_questions.append(
                {
                    "question_id": question_id,
                    "competency": competency,
                    "sub_competency": question.get(
                        "sub_competency"
                    ),
                    "question": question.get(
                        "question",
                        "",
                    ),
                    "evaluation_refs": refs,
                    "weak_concepts":
                        question_weak_concepts,
                }
            )

    # --------------------------------------------
    # REPORT
    # --------------------------------------------

    print("=" * 100)
    print("EVALUATION KNOWLEDGE CONCEPT COVERAGE")
    print("=" * 100)

    print(
        f"\nQuestions              : "
        f"{len(questions)}"
    )

    print(
        f"Evaluation records     : "
        f"{len(evaluations)}"
    )

    print(
        f"Questions without must-have concepts : "
        f"{len(empty_must_questions)}"
    )

    print(
        f"Invalid evaluation refs              : "
        f"{len(missing_refs)}"
    )

    # --------------------------------------------
    # Must-have coverage
    # --------------------------------------------

    must_pct = (
        covered_must / total_must * 100
        if total_must
        else 0
    )

    print("\n" + "-" * 100)
    print("MUST-HAVE CONCEPT LEXICAL COVERAGE")
    print("-" * 100)

    print(f"Total concepts   : {total_must}")
    print(f"Covered          : {covered_must}")
    print(
        f"Needs review     : "
        f"{total_must - covered_must}"
    )
    print(f"Coverage         : {must_pct:.2f}%")

    # --------------------------------------------
    # Bonus coverage
    # --------------------------------------------

    bonus_pct = (
        covered_bonus / total_bonus * 100
        if total_bonus
        else 0
    )

    print("\n" + "-" * 100)
    print("BONUS CONCEPT LEXICAL COVERAGE")
    print("-" * 100)

    print(f"Total concepts   : {total_bonus}")
    print(f"Covered          : {covered_bonus}")
    print(
        f"Needs review     : "
        f"{total_bonus - covered_bonus}"
    )
    print(f"Coverage         : {bonus_pct:.2f}%")

    # --------------------------------------------
    # By competency
    # --------------------------------------------

    print("\n" + "-" * 100)
    print("MUST-HAVE COVERAGE BY COMPETENCY")
    print("-" * 100)

    for competency, stats in sorted(
        competency_stats.items()
    ):

        total = stats["must_total"]
        covered = stats["must_covered"]

        pct = (
            covered / total * 100
            if total
            else 0
        )

        print(
            f"{competency:<35}"
            f"{covered:>4}/{total:<4}"
            f"{pct:>8.2f}%"
        )

    # --------------------------------------------
    # Empty must-have concepts
    # --------------------------------------------

    if empty_must_questions:

        print("\n" + "-" * 100)
        print("QUESTIONS WITHOUT MUST-HAVE CONCEPTS")
        print("-" * 100)

        for item in empty_must_questions:

            print(
                f"\n{item['question_id']}"
            )

            print(
                f"  Competency : "
                f"{item['competency']}"
            )

            print(
                f"  Refs       : "
                f"{item['evaluation_refs']}"
            )

            print(
                f"  Question   : "
                f"{item['question']}"
            )

    # --------------------------------------------
    # Weak lexical matches
    # --------------------------------------------

    if weak_questions:

        print("\n" + "-" * 100)
        print("CONCEPTS REQUIRING SEMANTIC REVIEW")
        print("-" * 100)

        for item in weak_questions:

            print(
                f"\n{item['question_id']} "
                f"[{item['competency']} / "
                f"{item['sub_competency']}]"
            )

            print(
                f"  Refs: "
                f"{item['evaluation_refs']}"
            )

            for concept in item[
                "weak_concepts"
            ]:

                print(
                    f"  - {concept['type']:<10} "
                    f"{concept['lexical_score']:<5} "
                    f"{concept['concept']}"
                )

    print("\n" + "=" * 100)

    print(
        "\nNOTE: Lexical coverage is a diagnostic only."
    )

    print(
        "Low lexical similarity does not prove that "
        "evaluation knowledge is insufficient."
    )

    print(
        "Low-scoring concepts should be checked "
        "semantically in Gate 2B."
    )


if __name__ == "__main__":
    main()
