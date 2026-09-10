"""
Evaluation RAG service for InterviewGapAI.

This module exposes the stable interface used by the Evaluation Agent.

The agent should use this service rather than interacting directly
with Pinecone or the dense retriever.
"""

from typing import List, Dict, Any
from src.observability import log_event, traced

from src.evaluation_rag.dense_retriever import (
    EvaluationDenseRetriever,
)


class EvaluationRAGService:
    """
    Production-facing interface for Evaluation RAG.

    Selected retrieval configuration:
        - OpenAI text-embedding-3-small
        - Pinecone dense retrieval
        - competency metadata filtering
        - top-k = 5
    """

    def __init__(self, k: int = 5):

        self.k = k

        self.retriever = EvaluationDenseRetriever(
            k=k
        )

    def build_query(
        self,
        question: str,
        candidate_answer: str,
    ) -> str:
        """
        Build the Evaluation RAG retrieval query.

        MVP retrieval uses the interview question only.

        Candidate answers are intentionally NOT included in retrieval because:
        1. The selected RAG configuration was evaluated using question-only queries.
        2. Incorrect candidate answers should not distort knowledge retrieval.
        3. Candidate answers are consumed later by the Evaluation Agent.
        """

        question = (question or "").strip()

        if not question:
            raise ValueError(
                "question must not be empty"
            )

        return question


    @traced("evaluation_rag.retrieve")
    def retrieve(
        self,
        question: str,
        candidate_answer: str,
        competency: str,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve evaluation knowledge for a candidate answer.
        """

        if not competency:
            raise ValueError(
                "competency must not be empty"
            )

        query = self.build_query(
            question=question,
            candidate_answer=candidate_answer,
        )

        results = self.retriever.retrieve(
            query=query,
            k=self.k,
            competency=competency,
        )

        log_event(
            "evaluation_rag.results", competency=competency, top_k=self.k,
            result_count=len(results),
            evidence=[{
                "evaluation_id": result["evaluation_id"],
                "rank": result["rank"], "score": result["score"],
            } for result in results],
        )
        return results


    @traced("evaluation_rag.retrieve_context")
    def retrieve_context(
        self,
        question: str,
        candidate_answer: str,
        competency: str,
    ) -> Dict[str, Any]:
        """
        Return Evaluation RAG results in a clean structure
        suitable for the Evaluation Agent.
        """

        results = self.retrieve(
            question=question,
            candidate_answer=candidate_answer,
            competency=competency,
        )

        return {
            "question": question,
            "competency": competency,
            "retrieved_knowledge": [
                {
                    "evaluation_id": result["evaluation_id"],
                    "rank": result["rank"],
                    "score": result["score"],
                    "content": result["search_text"],
                }
                for result in results
            ],
        }


_default_service = None


def get_evaluation_rag_service():
    """
    Return a reusable EvaluationRAGService instance.

    Avoid repeatedly creating OpenAI/Pinecone clients.
    """

    global _default_service

    if _default_service is None:
        _default_service = (
            EvaluationRAGService(k=5)
        )

    return _default_service


@traced("evaluation_rag.request")
def retrieve_evaluation_context(
    question: str,
    candidate_answer: str,
    competency: str,
):
    """
    Convenience function for Evaluation Agent integration.
    """

    service = get_evaluation_rag_service()

    return service.retrieve_context(
        question=question,
        candidate_answer=candidate_answer,
        competency=competency,
    )
