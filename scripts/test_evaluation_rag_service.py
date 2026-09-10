import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation_rag.service import (
    retrieve_evaluation_context,
)


def main():

    question = (
        "What do Recall@k, MRR, and MAP tell you "
        "about retrieval quality?"
    )

    candidate_answer = (
        "Recall tells us whether relevant documents "
        "were found, while MRR looks at ranking."
    )

    competency = "rag"

    results = retrieve_evaluation_context(
        question=question,
        candidate_answer=candidate_answer,
        competency=competency,
    )

    print("=" * 70)
    print("EVALUATION RAG SERVICE TEST")
    print("=" * 70)

    for result in results["retrieved_knowledge"]:

        print(
            f"{result['rank']}. "
            f"{result['evaluation_id']} "
            f"score={result['score']:.4f}"
        )


if __name__ == "__main__":
    main()
