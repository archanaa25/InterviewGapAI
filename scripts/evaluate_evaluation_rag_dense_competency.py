import json
import math
import sys
import time
from pathlib import Path
from statistics import mean
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Support direct execution as well as python -m scripts.evaluate_evaluation_rag_dense_competency.
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation_rag.dense_retriever import EvaluationDenseRetriever

GOLDEN_FILE = Path(
    "data/eval/evaluation_rag_golden.jsonl"
)

RESULTS_FILE = Path(
    "data/eval/evaluation_rag_dense_competency_results.jsonl"
)


def load_jsonl(path):
    records = []

    with path.open(
        encoding="utf-8"
    ) as f:
        for line in f:
            line = line.strip()

            if line:
                records.append(
                    json.loads(line)
                )

    return records


def recall_at_k(
    retrieved_ids,
    relevant_ids,
    k,
):
    """
    Fraction of relevant documents retrieved in top-k.
    """

    relevant = set(relevant_ids)

    if not relevant:
        return 0.0

    retrieved = set(
        retrieved_ids[:k]
    )

    return (
        len(relevant & retrieved)
        / len(relevant)
    )


def reciprocal_rank(
    retrieved_ids,
    relevant_ids,
):
    """
    Reciprocal rank of first relevant result.
    """

    relevant = set(relevant_ids)

    for rank, doc_id in enumerate(
        retrieved_ids,
        start=1,
    ):
        if doc_id in relevant:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(
    retrieved_ids,
    relevant_ids,
    k,
):
    """
    Binary-relevance NDCG@k.
    """

    relevant = set(relevant_ids)

    dcg = 0.0

    for rank, doc_id in enumerate(
        retrieved_ids[:k],
        start=1,
    ):
        if doc_id in relevant:
            dcg += (
                1.0
                / math.log2(rank + 1)
            )

    ideal_hits = min(
        len(relevant),
        k,
    )

    if ideal_hits == 0:
        return 0.0

    idcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(
            1,
            ideal_hits + 1,
        )
    )

    return dcg / idcg


def main():

    golden = load_jsonl(
        GOLDEN_FILE
    )

    retriever = (
        EvaluationDenseRetriever()
    )

    RESULTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    recall_1 = []
    recall_3 = []
    recall_5 = []

    reciprocal_ranks = []
    ndcg_5 = []

    latencies_ms = []

    results_output = []

    print(
        f"Evaluating {len(golden)} "
        f"golden queries...\n"
    )

    for index, item in enumerate(
        golden,
        start=1,
    ):

        start = time.perf_counter()

        results = retriever.retrieve(
            query=item["query"],
            competency=item["competency"],
            k=5,
        )

        elapsed_ms = (
            time.perf_counter()
            - start
        ) * 1000

        retrieved_ids = [
            result["evaluation_id"]
            for result in results
        ]

        relevant_ids = (
            item["relevant_ids"]
        )

        r1 = recall_at_k(
            retrieved_ids,
            relevant_ids,
            1,
        )

        r3 = recall_at_k(
            retrieved_ids,
            relevant_ids,
            3,
        )

        r5 = recall_at_k(
            retrieved_ids,
            relevant_ids,
            5,
        )

        rr = reciprocal_rank(
            retrieved_ids,
            relevant_ids,
        )

        n5 = ndcg_at_k(
            retrieved_ids,
            relevant_ids,
            5,
        )

        recall_1.append(r1)
        recall_3.append(r3)
        recall_5.append(r5)

        reciprocal_ranks.append(rr)
        ndcg_5.append(n5)

        latencies_ms.append(
            elapsed_ms
        )

        results_output.append(
            {
                "query_id": item[
                    "query_id"
                ],
                "query": item["query"],
                "relevant_ids": relevant_ids,
                "retrieved_ids": (
                    retrieved_ids
                ),
                "recall_at_1": r1,
                "recall_at_3": r3,
                "recall_at_5": r5,
                "reciprocal_rank": rr,
                "ndcg_at_5": n5,
                "latency_ms": (
                    elapsed_ms
                ),
            }
        )

        print(
            f"[{index:>3}/{len(golden)}] "
            f"{item['query_id']:<25} "
            f"top1={retrieved_ids[0] if retrieved_ids else 'NONE'}"
        )

    with RESULTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in results_output:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print("\n" + "=" * 70)
    print("EVALUATION RAG — DENSE COMPETENCY BASELINE")
    print("=" * 70)

    print(
        f"Queries          : "
        f"{len(golden)}"
    )

    print(
        f"Recall@1         : "
        f"{mean(recall_1):.4f}"
    )

    print(
        f"Recall@3         : "
        f"{mean(recall_3):.4f}"
    )

    print(
        f"Recall@5         : "
        f"{mean(recall_5):.4f}"
    )

    print(
        f"MRR              : "
        f"{mean(reciprocal_ranks):.4f}"
    )

    print(
        f"NDCG@5           : "
        f"{mean(ndcg_5):.4f}"
    )

    print(
        f"Avg latency      : "
        f"{mean(latencies_ms):.3f} ms"
    )

    print(
        f"\nResults saved    : "
        f"{RESULTS_FILE}"
    )


if __name__ == "__main__":
    main()
