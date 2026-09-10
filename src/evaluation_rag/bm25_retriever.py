import re
from typing import List, Dict, Any

from rank_bm25 import BM25Okapi

from src.evaluation_rag.document_builder import (
    build_evaluation_documents,
)


def tokenize(text: str) -> List[str]:
    """
    Lightweight tokenizer for BM25.

    Keeps alphanumeric technical terms and lowercases them.
    """
    return re.findall(r"[a-zA-Z0-9@^+.-]+", text.lower())


class EvaluationBM25Retriever:
    """
    BM25 retriever over the Evaluation RAG corpus.
    """

    def __init__(self):
        self.documents = build_evaluation_documents()

        if not self.documents:
            raise ValueError("Evaluation corpus is empty.")

        self.tokenized_corpus = [
            tokenize(doc.page_content)
            for doc in self.documents
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_corpus
        )

    def retrieve(
        self,
        query: str,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-k evaluation knowledge documents.
        """

        query_tokens = tokenize(query)

        scores = self.bm25.get_scores(
            query_tokens
        )

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
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
                    "rank": rank,
                    "evaluation_id": (
                        document.metadata[
                            "evaluation_id"
                        ]
                    ),
                    "score": float(scores[index]),
                    "document": document,
                }
            )

        return results