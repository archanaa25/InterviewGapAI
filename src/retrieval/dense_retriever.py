"""
InterviewGap AI - Dense Question Retriever

Uses:
    OpenAI text-embedding-3-small
    Pinecone dense vector search

Corpus:
    interviewgap-ai
    namespace: questions-v1

No metadata filtering is applied in E2.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

load_dotenv(
    PROJECT_ROOT / ".env"
)


class QuestionDenseRetriever:
    """
    Dense semantic retriever for InterviewGap
    interview questions.
    """

    def __init__(
        self,
        k=5,
    ):

        self.k = k

        self.index_name = os.getenv(
            "PINECONE_INDEX_NAME",
            "interviewgap-ai",
        )

        self.namespace = os.getenv(
            "PINECONE_QUESTION_NAMESPACE",
            "questions-v1",
        )

        self.embedding_model = os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        )

        pinecone_api_key = os.getenv(
            "PINECONE_API_KEY"
        )

        openai_api_key = os.getenv(
            "OPENAI_API_KEY"
        )

        if not pinecone_api_key:
            raise RuntimeError(
                "PINECONE_API_KEY is not configured."
            )

        if not openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        #
        # OpenAI client
        #
        self.openai_client = OpenAI(
            api_key=openai_api_key
        )

        #
        # Pinecone client
        #
        self.pinecone = Pinecone(
            api_key=pinecone_api_key
        )

        self.index = self.pinecone.Index(
            self.index_name
        )

    def _embed_query(
        self,
        query,
    ):
        """
        Convert query text into the same embedding
        representation used during corpus ingestion.
        """

        response = (
            self.openai_client
            .embeddings
            .create(
                model=self.embedding_model,
                input=query,
            )
        )

        return (
            response
            .data[0]
            .embedding
        )

    def search(
        self,
        query,
        k=None,
        filters=None,
    ):
        """
        Retrieve top-k semantically similar
        interview questions from Pinecone.

        Optional filters are passed to Pinecone's metadata filter parameter.
        Omitting filters preserves the unfiltered E2 search.
        """

        if k is None:
            k = self.k

        #
        # Step 1:
        # Embed user/retrieval query
        #
        query_vector = (
            self._embed_query(
                query
            )
        )

        #
        # Step 2:
        # Dense vector similarity search
        #
        query_options = {"filter": filters} if filters else {}
        response = self.index.query(
            namespace=self.namespace,
            vector=query_vector,
            top_k=k,
            include_metadata=True,
            **query_options,
        )

        #
        # Step 3:
        # Normalize Pinecone output into the
        # same structure used by BM25.
        #
        results = []

        for rank, match in enumerate(
            response.matches,
            start=1,
        ):

            metadata = (
                match.metadata
                or {}
            )

            search_text = (
                metadata.get(
                    "search_text",
                    "",
                )
            )

            question = (
                self._extract_question(
                    search_text
                )
            )

            results.append(
                {
                    "question_id":
                        match.id,

                    "rank":
                        rank,

                    "score":
                        float(
                            match.score
                        ),

                    "question":
                        question,

                    "competency":
                        metadata.get(
                            "competency"
                        ),

                    "sub_competency":
                        metadata.get(
                            "sub_competency"
                        ),

                    "difficulty":
                        metadata.get(
                            "difficulty"
                        ),

                    "question_type":
                        metadata.get(
                            "question_type"
                        ),
                }
            )

        return results

    @staticmethod
    def _extract_question(
        search_text,
    ):
        """
        Extract the original interview question
        from the searchable document representation.
        """

        if not search_text:
            return ""

        question_part = (
            search_text.split(
                "Must-have concepts:"
            )[0]
        )

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
    expected_id=None,
):

    print()
    print("=" * 80)
    print("DENSE RETRIEVAL TEST")
    print("=" * 80)

    print()
    print(
        f"Query:"
    )

    print(
        query
    )

    if expected_id:

        print()
        print(
            f"Expected target: "
            f"{expected_id}"
        )

    print()
    print(
        "Dense results:"
    )

    for result in results:

        marker = ""

        if (
            expected_id
            and result[
                "question_id"
            ]
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

    retriever = (
        QuestionDenseRetriever(
            k=5
        )
    )

    #
    # Golden case QG-031.
    #
    # BM25 failed this case.
    #
    query = (
        "The steps in my process are known "
        "in advance and rarely change. "
        "Should the model really be deciding "
        "what happens next?"
    )

    expected_id = (
        "AGENT-FUND-INT-001"
    )

    results = (
        retriever.search(
            query,
            k=5,
        )
    )

    print_results(
        query,
        results,
        expected_id,
    )


if __name__ == "__main__":
    main()
