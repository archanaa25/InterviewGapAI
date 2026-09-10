#!/usr/bin/env python3

"""
InterviewGap AI - Question Retrieval Evaluation

Evaluates a retriever against the golden question-retrieval dataset.

Current experiment:
    BM25

Metrics:
    Recall@1
    Recall@3
    Recall@5
    MRR
    NDCG@5
    Average latency

Later the same evaluation logic can be reused for:
    Dense / Pinecone
    Hybrid + RRF
    Hybrid + RRF + Reranker
"""

import json
import math
import time
from pathlib import Path
from statistics import mean
import argparse
from src.retrieval.bm25_retriever import (
    QuestionBM25Retriever,
)
from src.retrieval.dense_retriever import QuestionDenseRetriever
from src.retrieval.dense_metadata_retriever import (
    QuestionDenseMetadataRetriever,
)
from src.retrieval.metadata_filtered_dense_retriever import (
    MetadataFilteredDenseRetriever,
)

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

CORPUS_FILE = (
    PROJECT_ROOT
    / "data"
    / "prepared"
    / "master"
    / "interview_questions.jsonl"
)

GOLDEN_FILE = (
    PROJECT_ROOT
    / "data"
    / "eval"
    / "question_retrieval_golden.jsonl"
)

RESULT_DIR = (
    PROJECT_ROOT
    / "data"
    / "eval"
    / "results"
)





TOP_K = 5


def load_jsonl(path):
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:

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
    Fraction of relevant documents retrieved
    within top-k.

    For our current golden dataset there is
    usually one relevant question per query.
    """

    relevant = set(
        relevant_ids
    )

    retrieved = set(
        retrieved_ids[:k]
    )

    if not relevant:
        return 0.0

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

    Rank 1 -> 1.0
    Rank 2 -> 0.5
    Rank 3 -> 0.333...
    """

    relevant = set(
        relevant_ids
    )

    for rank, question_id in enumerate(
        retrieved_ids,
        start=1,
    ):

        if question_id in relevant:
            return 1.0 / rank

    return 0.0


def dcg_at_k(
    retrieved_ids,
    relevant_ids,
    k,
):
    """
    Discounted Cumulative Gain using
    binary relevance.
    """

    relevant = set(
        relevant_ids
    )

    dcg = 0.0

    for rank, question_id in enumerate(
        retrieved_ids[:k],
        start=1,
    ):

        relevance = (
            1.0
            if question_id in relevant
            else 0.0
        )

        dcg += (
            relevance
            / math.log2(rank + 1)
        )

    return dcg


def ndcg_at_k(
    retrieved_ids,
    relevant_ids,
    k,
):
    """
    Normalized Discounted Cumulative Gain.
    """

    actual_dcg = dcg_at_k(
        retrieved_ids,
        relevant_ids,
        k,
    )

    ideal_count = min(
        len(relevant_ids),
        k,
    )

    if ideal_count == 0:
        return 0.0

    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(
            1,
            ideal_count + 1,
        )
    )

    return actual_dcg / ideal_dcg


def evaluate_query(
    retriever,
    golden_record,
):
    query = golden_record[
        "query"
    ]

    relevant_ids = golden_record[
        "relevant_question_ids"
    ]

    #
    # Measure retrieval latency.
    #
    start = time.perf_counter()


    # Metadata-aware experiments use gold constraints from the dataset.
    # Their scores therefore assume correct upstream competency/difficulty
    # selection; they do not measure resume-analysis or planner accuracy.
    if getattr(retriever, "uses_metadata", False):

        results = retriever.search(
            query,
            k=TOP_K,
            metadata=golden_record,
        )

    else:

        results = retriever.search(
            query,
            k=TOP_K,
        )

    # results = retriever.search(
    #     query,
    #     k=TOP_K,
    # )

    latency_ms = (
        time.perf_counter() - start
    ) * 1000

    retrieved_ids = [
        result["question_id"]
        for result in results
    ]

    metrics = {
        "recall_at_1":
            recall_at_k(
                retrieved_ids,
                relevant_ids,
                1,
            ),

        "recall_at_3":
            recall_at_k(
                retrieved_ids,
                relevant_ids,
                3,
            ),

        "recall_at_5":
            recall_at_k(
                retrieved_ids,
                relevant_ids,
                5,
            ),

        "reciprocal_rank":
            reciprocal_rank(
                retrieved_ids,
                relevant_ids,
            ),

        "ndcg_at_5":
            ndcg_at_k(
                retrieved_ids,
                relevant_ids,
                5,
            ),
    }

    return {
        "expected_behavior": golden_record.get("expected_behavior", "retrieve"),

        "query_id":
            golden_record[
                "query_id"
            ],

        "query":
            query,

        "query_type":
            golden_record[
                "query_type"
            ],

        "expected_competency":
            golden_record[
                "expected_competency"
            ],

        "expected_sub_competency":
            golden_record[
                "expected_sub_competency"
            ],

        "relevant_question_ids":
            relevant_ids,

        "retrieved_question_ids":
            retrieved_ids,

        "retrieved_results": [
            {
                "rank":
                    result["rank"],

                "question_id":
                    result["question_id"],

                "score":
                    result["score"],

                "competency":
                    result["competency"],

                "sub_competency":
                    result[
                        "sub_competency"
                    ],

                "difficulty":
                    result["difficulty"],
            }
            for result in results
        ],

        "metrics":
            metrics,

        "latency_ms":
            latency_ms,
    }


def calculate_summary(query_results):
    """Score retrieval queries; report negative-query counts separately."""
    retrieval_results = [r for r in query_results if not is_negative_query(r)]
    summary = {
        "total_queries": len(query_results),
        "retrieval_queries": len(retrieval_results),
        "negative_queries": len(query_results) - len(retrieval_results),
        "average_latency_ms": (
            mean(r["latency_ms"] for r in query_results) if query_results else 0.0
        ),
    }
    for name in ("recall_at_1", "recall_at_3", "recall_at_5",
                 "reciprocal_rank", "ndcg_at_5"):
        output_name = "mrr" if name == "reciprocal_rank" else name
        summary[output_name] = (
            mean(r["metrics"][name] for r in retrieval_results)
            if retrieval_results else None
        )
    return summary


def is_negative_query(result):
    return result.get("expected_behavior") == "no_relevant_question"


def calculate_query_type_breakdown(query_results):
    """Apply the same summary metrics to each query type."""
    return {
        query_type: calculate_summary([
            r for r in query_results if r["query_type"] == query_type
        ])
        for query_type in sorted({r["query_type"] for r in query_results})
    }


def print_query_result(index, total, result):
    """Print query progress and the retrieved question IDs."""
    if is_negative_query(result):
        status = "NEGATIVE (abstention not scored)"
    else:
        status = "PASS" if result["metrics"]["recall_at_5"] > 0 else "FAIL"
    print(f"[{index:02d}/{total:02d}] {result['query_id']}: {status}")
    print(f"  Query: {result['query']}")
    print("  Expected: " + (", ".join(result["relevant_question_ids"]) or "none"))
    print("  Retrieved: " + (", ".join(result["retrieved_question_ids"]) or "none"))


def print_negative_queries(query_results):
    """Report out-of-scope queries without treating them as retrieval failures."""
    negatives = [r for r in query_results if is_negative_query(r)]
    print(f"\nNEGATIVE QUERIES: {len(negatives)} (abstention not scored)")
    for result in negatives:
        retrieved = ", ".join(result["retrieved_question_ids"]) or "none"
        print(f"  {result['query_id']}: {retrieved}")


def print_summary(
    summary,
    breakdown,
    retriever_name,
):

    print()
    print("=" * 70)
    print(
    f"INTERVIEWGAP AI - "
    f"{retriever_name.upper()} "
    f"RETRIEVAL EVALUATION V2"
    )
    print("=" * 70)

    print()
    print(
        f"Golden queries    : "
        f"{summary['total_queries']}"
    )

    print(f"Retrieval queries : {summary['retrieval_queries']}")
    print(f"Negative queries  : {summary['negative_queries']}")
    if not summary["retrieval_queries"]:
        print("No retrieval queries to score.")
        return

    print()
    print("Retrieval Quality")
    print("-----------------")

    print(
        f"Recall@1          : "
        f"{summary['recall_at_1']:.4f}"
    )

    print(
        f"Recall@3          : "
        f"{summary['recall_at_3']:.4f}"
    )

    print(
        f"Recall@5          : "
        f"{summary['recall_at_5']:.4f}"
    )

    print(
        f"MRR               : "
        f"{summary['mrr']:.4f}"
    )

    print(
        f"NDCG@5            : "
        f"{summary['ndcg_at_5']:.4f}"
    )

    print()
    print("Performance")
    print("-----------")

    print(
        f"Average latency   : "
        f"{summary['average_latency_ms']:.3f} ms"
    )

    print("\nQuality by query type (negative queries excluded)")
    for query_type, metrics in breakdown.items():
        if metrics["retrieval_queries"]:
            print(f"  {query_type}: Recall@5={metrics['recall_at_5']:.4f}, "
                  f"MRR={metrics['mrr']:.4f}")


def print_failures(
    query_results,
):
    """
    Show queries where the correct question
    did not appear in top-5.
    """

    failures = [
        result
        for result in query_results
        if not is_negative_query(result) and result["metrics"][
            "recall_at_5"
        ] == 0
    ]

    print()
    print("=" * 70)
    print("TOP-5 FAILURES")
    print("=" * 70)

    if not failures:

        print()
        print(
            "No Top-5 failures. "
            "All golden targets were retrieved."
        )

        return

    for result in failures:

        print()
        print(
            f"Query ID : "
            f"{result['query_id']}"
        )

        print(
            f"Query    : "
            f"{result['query']}"
        )

        print(
            "Expected : "
            + ", ".join(
                result[
                    "relevant_question_ids"
                ]
            )
        )

        print(
            "Retrieved: "
            + ", ".join(
                result[
                    "retrieved_question_ids"
                ]
            )
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate InterviewGap question retrieval"
    )

    parser.add_argument(
        "--retriever",
        choices=["bm25", "dense", "hybrid","dense_competency","dense_competency_difficulty","dense_full_metadata"],
        required=True,
        help="Retriever to evaluate",
    )

    return parser.parse_args()


def create_retriever(retriever_name):

    if retriever_name == "hybrid":
        from src.retrieval.hybrid_retriever import QuestionHybridRetriever

        retriever = QuestionHybridRetriever(k=TOP_K)
        return retriever, len(retriever.bm25.documents)

    if retriever_name == "bm25":

        retriever = QuestionBM25Retriever(
            corpus_path=CORPUS_FILE,
            k=TOP_K,
        )

        corpus_size = len(
            retriever.documents
        )

        return retriever, corpus_size

    if retriever_name == "dense":

        retriever = QuestionDenseRetriever(
            k=TOP_K
        )

        # We already know the Pinecone namespace
        # contains the complete question corpus.
        corpus_size = 112

        return retriever, corpus_size

    if retriever_name == "dense_metadata":

        retriever = (
            QuestionDenseMetadataRetriever(
                k=TOP_K
            )
        )

        return retriever, 112

    if retriever_name == "dense_competency":

        retriever = MetadataFilteredDenseRetriever(
            k=TOP_K,
            filter_mode="competency",
        )

        return retriever, 112

    if retriever_name == "dense_competency_difficulty":

        retriever = MetadataFilteredDenseRetriever(
            k=TOP_K,
            filter_mode="competency_difficulty",
        )

        return retriever, 112

    if retriever_name == "dense_full_metadata":

        retriever = MetadataFilteredDenseRetriever(
            k=TOP_K,
            filter_mode="full",
        )

        return retriever, 112

    raise ValueError(
        f"Unsupported retriever: {retriever_name}"
    )

def main():

    args = parse_args()

    retriever_name = (
        args.retriever
    )

    print()
    print("=" * 75)
    print(
        f"INTERVIEWGAP AI - "
        f"{retriever_name.upper()} "
        f"RETRIEVAL EVALUATION"
    )
    print("=" * 75)

    print()
    print(
        f"Loading golden dataset: "
        f"{GOLDEN_FILE}"
    )

    golden_records = load_jsonl(
        GOLDEN_FILE
    )

    print(
        f"Golden queries: "
        f"{len(golden_records)}"
    )

    print()
    print(
        f"Creating retriever: "
        f"{retriever_name}"
    )

    retriever, corpus_size = (
        create_retriever(
            retriever_name
        )
    )

    print(
        f"Corpus size: "
        f"{corpus_size}"
    )

    print()
    print(
        f"Running "
        f"{retriever_name.upper()} "
        f"retrieval evaluation..."
    )

    query_results = []

    for index, golden_record in enumerate(
        golden_records,
        start=1,
    ):

        result = evaluate_query(
            retriever,
            golden_record,
        )

        query_results.append(
            result
        )

        print_query_result(
            index,
            len(golden_records),
            result,
        )

    summary = calculate_summary(
        query_results
    )

    breakdown = (
        calculate_query_type_breakdown(
            query_results
        )
    )

    print_summary(
        summary,
        breakdown,
        retriever_name,
    )

    print_failures(
        query_results
    )

    print_negative_queries(
        query_results
    )

    RESULT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_file = (
        RESULT_DIR
        / f"{retriever_name}_results_v2.json"
    )

    experiment = {

        "experiment_id":
            f"question-retrieval-"
            f"{retriever_name}-v2",

        "retriever":
            retriever_name,

        "top_k":
            TOP_K,

        "corpus_size":
            corpus_size,

        "golden_dataset":
            GOLDEN_FILE.name,

        "summary":
            summary,

        "query_type_breakdown":
            breakdown,

        "query_results":
            query_results,
    }

    result_file.write_text(
        json.dumps(
            experiment,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "Results saved to:"
    )

    print(
        f"  {result_file}"
    )


if __name__ == "__main__":
    main()

# def main():

#     print(
#         f"Loading golden dataset: "
#         f"{GOLDEN_FILE}"
#     )

#     golden_records = load_jsonl(
#         GOLDEN_FILE
#     )

#     print(
#         f"Golden queries: "
#         f"{len(golden_records)}"
#     )

#     print()
#     print(
#         f"Loading question corpus: "
#         f"{CORPUS_FILE}"
#     )

#     retriever = QuestionBM25Retriever(
#         corpus_path=CORPUS_FILE,
#         k=TOP_K,
#     )

#     print(
#         f"BM25 corpus size: "
#         f"{len(retriever.documents)}"
#     )

#     query_results = []

#     print()
#     print(
#         "Running BM25 retrieval evaluation..."
#     )

#     for index, golden_record in enumerate(
#         golden_records,
#         start=1,
#     ):

#         result = evaluate_query(
#             retriever,
#             golden_record,
#         )

#         query_results.append(
#             result
#         )

#         hit = (
#             "PASS"
#             if result["metrics"][
#                 "recall_at_5"
#             ] > 0
#             else "FAIL"
#         )

#         print()
#         print("=" * 90)

#         print(
#             f"[{index:02d}/{len(golden_records):02d}] "
#             f"{golden_record['query_id']}"
#         )

#         print(
#             f"Question     : "
#             f"{golden_record['query']}"
#         )

#         print(
#             "Expected ID  : "
#             + ", ".join(
#                 golden_record[
#                     "relevant_question_ids"
#                 ]
#             )
#         )

#         print(
#             "Retrieved IDs:"
#         )

#         for retrieved in result["retrieved_results"]:

#             marker = ""

#             if (
#                 retrieved["question_id"]
#                 in golden_record[
#                     "relevant_question_ids"
#                 ]
#             ):
#                 marker = " <-- EXPECTED"

#             print(
#                 f"  {retrieved['rank']}. "
#                 f"{retrieved['question_id']}"
#                 f"{marker}"
#             )

#         print(
#             f"Result       : {hit}"
#         )



#     summary = calculate_summary(
#         query_results
#     )

#     print_summary(
#         summary
#     )

#     print_failures(
#         query_results
#     )

#     #
#     # Save complete experiment.
#     #
#     RESULT_DIR.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     experiment = {
#         "experiment_id":
#             "question-retrieval-bm25-v1",

#         "retriever":
#             "bm25",

#         "top_k":
#             TOP_K,

#         "corpus_size":
#             len(
#                 retriever.documents
#             ),

#         "golden_dataset":
#             GOLDEN_FILE.name,

#         "summary":
#             summary,

#         "query_results":
#             query_results,
#     }

#     RESULT_FILE.write_text(
#         json.dumps(
#             experiment,
#             indent=2,
#             ensure_ascii=False,
#         ),
#         encoding="utf-8",
#     )

#     print()
#     print(
#         f"Results saved to:"
#     )

#     print(
#         f"  {RESULT_FILE}"
#     )


# if __name__ == "__main__":
#     main()
