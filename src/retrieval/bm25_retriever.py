"""
InterviewGap AI - BM25 Question Retriever

Sparse / lexical retrieval baseline over the
112-question InterviewGap corpus.
"""

import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from src.corpus.document_builder import (
    build_question_documents,
)


def bm25_preprocess(text):
    """
    Normalize text for BM25.

    Inspired by the course hybrid-retrieval notebook:
    lowercase and remove punctuation so terms such as
    'BM25?' and 'BM25' match.

    Keeps hyphenated terms reasonably searchable while
    avoiding punctuation-related misses.
    """

    return re.findall(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        text.lower(),
    )


class QuestionBM25Retriever:
    """
    BM25 retriever for InterviewGap interview questions.
    """

    def __init__(
        self,
        corpus_path,
        k=5,
    ):
        self.corpus_path = Path(corpus_path)
        self.k = k

        #
        # Same LangChain Documents that will later
        # be used for Dense/Pinecone retrieval.
        #
        self.documents = build_question_documents(
            self.corpus_path
        )

        if not self.documents:
            raise ValueError(
                "Question corpus is empty."
            )

        #
        # BM25 works on tokenized text.
        #
        self.tokenized_corpus = [
            bm25_preprocess(
                document.page_content
            )
            for document in self.documents
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_corpus
        )

    def search(
        self,
        query,
        k=None,
    ):
        """
        Search the complete question corpus.

        Returns:
            list[dict]
        """

        if k is None:
            k = self.k

        query_tokens = bm25_preprocess(
            query
        )

        scores = self.bm25.get_scores(
            query_tokens
        )

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[:k]

        results = []

        for rank, index in enumerate(
            ranked_indices,
            start=1,
        ):
            document = self.documents[index]

            results.append(
                {
                    "question_id":
                        document.metadata[
                            "question_id"
                        ],

                    "rank": rank,

                    "score":
                        float(scores[index]),

                    "question":
                        self._extract_question(
                            document.page_content
                        ),

                    "competency":
                        document.metadata[
                            "competency"
                        ],

                    "sub_competency":
                        document.metadata[
                            "sub_competency"
                        ],

                    "difficulty":
                        document.metadata[
                            "difficulty"
                        ],

                    "question_type":
                        document.metadata[
                            "question_type"
                        ],

                    # Keep original document because
                    # Hybrid/RRF will need it later.
                    "document":
                        document,
                }
            )

        return results

    @staticmethod
    def _extract_question(page_content):
        """
        Extract only the actual interview question
        for display.
        """

        question_part = page_content.split(
            "Must-have concepts:"
        )[0]

        return (
            question_part
            .replace(
                "Question:",
                "",
                1,
            )
            .strip()
        )


def print_results(
    query,
    results,
):
    print()
    print("=" * 80)
    print("QUERY")
    print("=" * 80)
    print(query)

    print()
    print("=" * 80)
    print("BM25 RESULTS")
    print("=" * 80)

    for result in results:

        print()
        print(
            f"Rank        : "
            f"{result['rank']}"
        )

        print(
            f"Question ID : "
            f"{result['question_id']}"
        )

        print(
            f"Score       : "
            f"{result['score']:.4f}"
        )

        print(
            f"Competency  : "
            f"{result['competency']}"
        )

        print(
            f"Sub-comp    : "
            f"{result['sub_competency']}"
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

    project_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    corpus_path = (
        project_root
        / "data"
        / "prepared"
        / "master"
        / "interview_questions.jsonl"
    )

    retriever = QuestionBM25Retriever(
        corpus_path=corpus_path,
        k=5,
    )

    print(
        f"BM25 corpus: "
        f"{len(retriever.documents)} documents"
    )

    #
    # Same scenario represented by golden
    # query QG-004.
    #
    query = (
        "Semantic search misses SKU codes "
        "and exact identifiers. "
        "How should retrieval be improved?"
    )

    results = retriever.search(
        query,
        k=5,
    )

    print_results(
        query,
        results,
    )


if __name__ == "__main__":
    main()