"""
InterviewGapAI - Dense Evaluation Knowledge Retriever.

Uses:
    OpenAI text-embedding-3-small
    Pinecone dense vector search

Namespace:
    evaluation-v1
"""

import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from src.observability import trace_span, traced


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


class EvaluationEvidence(TypedDict):
    """JSON-serializable evidence returned in descending similarity order."""

    evaluation_id: str
    rank: int
    score: float
    competency: str | None
    sub_competency: str | None
    topic: str | None
    search_text: str


class EvaluationDenseRetriever:
    """Reuse one instance to retrieve evidence for the Evaluation Agent."""

    def __init__(self, k=5):

        self.k = k

        self.index_name = os.getenv(
            "PINECONE_INDEX_NAME",
            "interviewgap-ai",
        )

        self.namespace = os.getenv(
            "PINECONE_EVALUATION_NAMESPACE",
            "evaluation-v1",
        ) or "evaluation-v1"

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

        self.openai_client = OpenAI(
            api_key=openai_api_key
        )

        self.pinecone = Pinecone(
            api_key=pinecone_api_key
        )

        self.index = self.pinecone.Index(
            self.index_name
        )

    def retrieve(
        self,
        query: str,
        competency: str,
        k: int = 5,
    ) -> list[EvaluationEvidence]:
        """Retrieve up to k evidence records within one exact competency.

        Pass the interview question as query and its corpus competency slug.
        Empty results stay empty; service errors propagate to the caller.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")
        if not isinstance(competency, str) or not competency.strip():
            raise ValueError("competency must be a non-empty string.")
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("k must be a positive integer.")

        return self.search(
            query=query,
            k=k,
            filters={"competency": competency.strip()},
        )

    def _embed_query(self, query):

        with trace_span(
            "evaluation_rag.embed_query", model=self.embedding_model,
        ) as span:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=query,
            )
            span.set_attributes(total_tokens=response.usage.total_tokens)

        return response.data[0].embedding

    @traced("evaluation_rag.dense_search")
    def search(
        self,
        query,
        k=None,
        filters=None,
    ) -> list[EvaluationEvidence]:

        if k is None:
            k = self.k

        query_vector = self._embed_query(
            query
        )

        query_options = (
            {"filter": filters}
            if filters
            else {}
        )

        with trace_span(
            "evaluation_rag.pinecone_search", namespace=self.namespace,
            top_k=k, filters=filters,
        ) as span:
            response = self.index.query(
                namespace=self.namespace,
                vector=query_vector,
                top_k=k,
                include_metadata=True,
                **query_options,
            )
            span.set_attributes(result_count=len(response.matches))

        results = []

        for rank, match in enumerate(
            response.matches,
            start=1,
        ):

            metadata = match.metadata or {}

            results.append(
                {
                    "evaluation_id": match.id,
                    "rank": rank,
                    "score": float(
                        match.score
                    ),
                    "competency": (
                        metadata.get(
                            "competency"
                        )
                    ),
                    "sub_competency": (
                        metadata.get(
                            "sub_competency"
                        )
                    ),
                    "topic": metadata.get(
                        "topic"
                    ),
                    "search_text": (
                        metadata.get(
                            "search_text",
                            "",
                        )
                    ),
                }
            )

        return results
