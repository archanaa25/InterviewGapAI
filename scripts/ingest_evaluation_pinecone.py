"""
Ingest InterviewGapAI Evaluation RAG corpus into Pinecone.

Uses:
    OpenAI text-embedding-3-small
    Pinecone index: interviewgap-ai
    namespace: evaluation-v1
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

from src.evaluation_rag.document_builder import (
    build_evaluation_documents,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME",
    "interviewgap-ai",
)

NAMESPACE = os.getenv(
    "PINECONE_EVALUATION_NAMESPACE",
    "evaluation-v1",
)

EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

BATCH_SIZE = 50


def validate_config():

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    if not PINECONE_API_KEY:
        raise RuntimeError(
            "PINECONE_API_KEY is not configured."
        )


def embed_batch(client, texts):

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return [
        item.embedding
        for item in response.data
    ]


def main():

    validate_config()

    documents = build_evaluation_documents()

    print(
        f"Evaluation documents : {len(documents)}"
    )

    if not documents:
        raise RuntimeError(
            "No Evaluation RAG documents available."
        )

    openai_client = OpenAI(
        api_key=OPENAI_API_KEY
    )

    pc = Pinecone(
        api_key=PINECONE_API_KEY
    )

    #
    # We intentionally reuse the existing Pinecone index.
    # Do NOT create/delete/reconfigure the Question RAG index.
    #
    index = pc.Index(INDEX_NAME)

    print(f"Embedding model      : {EMBEDDING_MODEL}")
    print(f"Pinecone index       : {INDEX_NAME}")
    print(f"Namespace            : {NAMESPACE}")

    total = len(documents)

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        batch = documents[
            start:start + BATCH_SIZE
        ]

        texts = [
            document.page_content
            for document in batch
        ]

        embeddings = embed_batch(
            openai_client,
            texts,
        )

        vectors = []

        for document, embedding in zip(
            batch,
            embeddings,
        ):

            metadata = dict(
                document.metadata
            )

            # Useful for inspection/debugging.
            metadata["search_text"] = (
                document.page_content
            )

            evaluation_id = metadata[
                "evaluation_id"
            ]

            vectors.append(
                {
                    "id": evaluation_id,
                    "values": embedding,
                    "metadata": metadata,
                }
            )

        index.upsert(
            vectors=vectors,
            namespace=NAMESPACE,
        )

        print(
            f"Upserted "
            f"{min(start + len(batch), total)}"
            f"/{total}"
        )

    print("\nEvaluation RAG ingestion complete.")

    stats = index.describe_index_stats()

    print("\nIndex statistics:")
    print(stats)


if __name__ == "__main__":
    main()