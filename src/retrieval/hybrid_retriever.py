"""
InterviewGap AI - Hybrid Question Retriever

Combines:
    BM25 sparse retrieval
    Pinecone dense retrieval
    Reciprocal Rank Fusion (RRF)

E3 configuration:
    BM25 candidate pool  : Top 10
    Dense candidate pool : Top 10
    Final result         : Top 5

No metadata filtering yet.
No reranking yet.
"""

from pathlib import Path

from src.retrieval.bm25_retriever import (
    QuestionBM25Retriever,
)

from src.retrieval.dense_retriever import (
    QuestionDenseRetriever,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

CORPUS_FILE = (
    PROJECT_ROOT
    / "data"
    / "prepared"
    / "master"
    / "interview_questions.jsonl"
)


class QuestionHybridRetriever:

    def __init__(
        self,
        k=5,
        candidate_k=10,
        rrf_k=60,
    ):
        """
        Args:
            k:
                Number of final results.

            candidate_k:
                Number of candidates retrieved
                independently from BM25 and Dense.

            rrf_k:
                RRF rank constant.

                Standard RRF commonly uses 60.
        """

        self.k = k
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k

        self.bm25 = (
            QuestionBM25Retriever(
                corpus_path=CORPUS_FILE,
                k=candidate_k,
            )
        )

        self.dense = (
            QuestionDenseRetriever(
                k=candidate_k,
            )
        )

    def _rrf_score(
        self,
        rank,
    ):
        """
        Reciprocal Rank Fusion:

        score = 1 / (rrf_k + rank)

        We use ranks rather than raw BM25 /
        cosine similarity scores because the
        raw score scales are incompatible.
        """

        return (
            1.0
            / (
                self.rrf_k
                + rank
            )
        )

    def search(
        self,
        query,
        k=None,
    ):
        """
        Run BM25 + Dense retrieval and fuse
        their rankings using RRF.
        """

        if k is None:
            k = self.k

        #
        # Stage 1:
        # Independent candidate retrieval
        #
        bm25_results = (
            self.bm25.search(
                query,
                k=self.candidate_k,
            )
        )

        dense_results = (
            self.dense.search(
                query,
                k=self.candidate_k,
            )
        )

        #
        # Stage 2:
        # Accumulate RRF scores by question ID.
        #
        fused = {}

        for result in bm25_results:

            question_id = (
                result["question_id"]
            )

            if question_id not in fused:

                fused[question_id] = {
                    "question_id":
                        question_id,

                    "question":
                        result[
                            "question"
                        ],

                    "competency":
                        result[
                            "competency"
                        ],

                    "sub_competency":
                        result[
                            "sub_competency"
                        ],

                    "difficulty":
                        result[
                            "difficulty"
                        ],

                    "question_type":
                        result[
                            "question_type"
                        ],

                    "rrf_score":
                        0.0,

                    "bm25_rank":
                        None,

                    "dense_rank":
                        None,

                    "bm25_score":
                        None,

                    "dense_score":
                        None,
                }

            fused[
                question_id
            ][
                "bm25_rank"
            ] = result["rank"]

            fused[
                question_id
            ][
                "bm25_score"
            ] = result["score"]

            fused[
                question_id
            ][
                "rrf_score"
            ] += self._rrf_score(
                result["rank"]
            )

        for result in dense_results:

            question_id = (
                result["question_id"]
            )

            if question_id not in fused:

                fused[question_id] = {
                    "question_id":
                        question_id,

                    "question":
                        result[
                            "question"
                        ],

                    "competency":
                        result[
                            "competency"
                        ],

                    "sub_competency":
                        result[
                            "sub_competency"
                        ],

                    "difficulty":
                        result[
                            "difficulty"
                        ],

                    "question_type":
                        result[
                            "question_type"
                        ],

                    "rrf_score":
                        0.0,

                    "bm25_rank":
                        None,

                    "dense_rank":
                        None,

                    "bm25_score":
                        None,

                    "dense_score":
                        None,
                }

            fused[
                question_id
            ][
                "dense_rank"
            ] = result["rank"]

            fused[
                question_id
            ][
                "dense_score"
            ] = result["score"]

            fused[
                question_id
            ][
                "rrf_score"
            ] += self._rrf_score(
                result["rank"]
            )

        #
        # Stage 3:
        # Sort by combined RRF score.
        #
        ranked = sorted(
            fused.values(),
            key=lambda item:
                item["rrf_score"],
            reverse=True,
        )

        #
        # Stage 4:
        # Return final Top-K.
        #
        results = []

        for rank, result in enumerate(
            ranked[:k],
            start=1,
        ):

            results.append(
                {
                    "question_id":
                        result[
                            "question_id"
                        ],

                    "rank":
                        rank,

                    # Keep the field named score so
                    # our existing evaluator works.
                    "score":
                        result[
                            "rrf_score"
                        ],

                    "question":
                        result[
                            "question"
                        ],

                    "competency":
                        result[
                            "competency"
                        ],

                    "sub_competency":
                        result[
                            "sub_competency"
                        ],

                    "difficulty":
                        result[
                            "difficulty"
                        ],

                    "question_type":
                        result[
                            "question_type"
                        ],

                    #
                    # Debug information.
                    #
                    "bm25_rank":
                        result[
                            "bm25_rank"
                        ],

                    "dense_rank":
                        result[
                            "dense_rank"
                        ],

                    "bm25_score":
                        result[
                            "bm25_score"
                        ],

                    "dense_score":
                        result[
                            "dense_score"
                        ],
                }
            )

        return results


def print_results(
    query,
    results,
    expected_id=None,
):

    print()
    print("=" * 90)
    print("HYBRID RRF RETRIEVAL TEST")
    print("=" * 90)

    print()
    print("Query:")
    print(query)

    if expected_id:

        print()
        print(
            f"Expected target: "
            f"{expected_id}"
        )

    print()
    print("Hybrid results:")

    for result in results:

        marker = ""

        if (
            expected_id
            and result["question_id"]
            == expected_id
        ):

            marker = (
                " <-- EXPECTED"
            )

        print()
        print(
            f"Rank        : "
            f"{result['rank']}"
        )

        print(
            f"Question ID : "
            f"{result['question_id']}"
            f"{marker}"
        )

        print(
            f"RRF Score   : "
            f"{result['score']:.6f}"
        )

        print(
            f"BM25 Rank   : "
            f"{result['bm25_rank']}"
        )

        print(
            f"Dense Rank  : "
            f"{result['dense_rank']}"
        )

        print(
            f"Competency  : "
            f"{result['competency']}"
        )

        print(
            f"Difficulty  : "
            f"{result['difficulty']}"
        )

        print(
            f"Question    : "
            f"{result['question']}"
        )


def main():

    retriever = (
        QuestionHybridRetriever(
            k=5,
            candidate_k=10,
            rrf_k=60,
        )
    )

    #
    # QG-031
    #
    # BM25:
    #   expected question NOT in Top-5
    #
    # Dense:
    #   expected question Rank 5
    #
    # Let's see what RRF does.
    #
    query = (
        "The steps in my process are "
        "known in advance and rarely "
        "change. Should the model really "
        "be deciding what happens next?"
    )

    expected_id = (
        "AGENT-FUND-INT-001"
    )

    results = retriever.search(
        query,
        k=5,
    )

    print_results(
        query,
        results,
        expected_id,
    )


if __name__ == "__main__":
    main()
