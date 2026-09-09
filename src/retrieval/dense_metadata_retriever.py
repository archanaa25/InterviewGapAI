"""
InterviewGap AI - Metadata-Aware Dense Retriever

Uses Pinecone dense semantic retrieval with structured
interview constraints.

E4 experiment.
"""

from src.retrieval.dense_retriever import (
    QuestionDenseRetriever,
)


class QuestionDenseMetadataRetriever:

    uses_metadata = True

    def __init__(
        self,
        k=5,
    ):
        self.k = k

        self.dense = (
            QuestionDenseRetriever(
                k=k
            )
        )

    def search(
        self,
        query,
        k=None,
        metadata=None,
    ):

        if k is None:
            k = self.k

        filters = {}

        if metadata:

            competency = metadata.get(
                "expected_competency"
            )

            sub_competency = metadata.get(
                "expected_sub_competency"
            )

            difficulty = metadata.get(
                "difficulty_target"
            )

            if competency is not None:
                filters[
                    "competency"
                ] = competency

            if sub_competency is not None:
                filters[
                    "sub_competency"
                ] = sub_competency

            if difficulty is not None:
                filters[
                    "difficulty"
                ] = difficulty

        return self.dense.search(
            query,
            k=k,
            filters=filters or None,
        )
