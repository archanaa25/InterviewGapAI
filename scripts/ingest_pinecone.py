#!/usr/bin/env python3

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from src.corpus.document_builder import (
    build_question_documents,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


CORPUS_FILE = (
    PROJECT_ROOT
    / "data"
    / "prepared"
    / "master"
    / "interview_questions.jsonl"
)


PINECONE_API_KEY = os.getenv(
    "PINECONE_API_KEY"
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME",
    "interviewgap-ai",
)

NAMESPACE = os.getenv(
    "PINECONE_QUESTION_NAMESPACE",
    "questions-v1",
)

EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

PINECONE_CLOUD = os.getenv(
    "PINECONE_CLOUD",
    "aws",
)

PINECONE_REGION = os.getenv(
    "PINECONE_REGION",
    "us-east-1",
)


EMBEDDING_DIMENSION = 1536
BATCH_SIZE = 50


def validate_config():

    missing = []

    if not PINECONE_API_KEY:
        missing.append(
            "PINECONE_API_KEY"
        )

    if not OPENAI_API_KEY:
        missing.append(
            "OPENAI_API_KEY"
        )

    if missing:

        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing)
        )


def create_index_if_needed(
    pc,
):

    if pc.has_index(
        INDEX_NAME
    ):

        print(
            f"Pinecone index already exists: "
            f"{INDEX_NAME}"
        )

        description = pc.describe_index(
            INDEX_NAME
        )

        if (
            description.dimension
            != EMBEDDING_DIMENSION
        ):

            raise RuntimeError(
                f"Existing index dimension is "
                f"{description.dimension}, "
                f"expected "
                f"{EMBEDDING_DIMENSION}"
            )

        return

    print(
        f"Creating Pinecone index: "
        f"{INDEX_NAME}"
    )

    pc.create_index(
        name=INDEX_NAME,
        vector_type="dense",
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION,
        ),
        deletion_protection="disabled",
        tags={
            "application":
                "interviewgap-ai",
            "environment":
                "development",
        },
    )

    print(
        "Waiting for index to become ready..."
    )

    while True:

        description = pc.describe_index(
            INDEX_NAME
        )

        if description.status["ready"]:
            break

        time.sleep(2)

    print(
        "Pinecone index is ready."
    )


def embed_batch(
    client,
    texts,
):

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

    print(
        f"Loading corpus: {CORPUS_FILE}"
    )

    documents = (
        build_question_documents(
            CORPUS_FILE
        )
    )

    print(
        f"Question documents: "
        f"{len(documents)}"
    )

    if not documents:

        raise RuntimeError(
            "No documents available "
            "for ingestion."
        )

    openai_client = OpenAI(
        api_key=OPENAI_API_KEY
    )

    pc = Pinecone(
        api_key=PINECONE_API_KEY
    )

    create_index_if_needed(
        pc
    )

    index = pc.Index(
        INDEX_NAME
    )

    print()
    print(
        f"Embedding model : "
        f"{EMBEDDING_MODEL}"
    )

    print(
        f"Index           : "
        f"{INDEX_NAME}"
    )

    print(
        f"Namespace       : "
        f"{NAMESPACE}"
    )

    print()

    total = len(
        documents
    )

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        batch = documents[
            start:
            start + BATCH_SIZE
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

            #
            # Keep the searchable text in
            # metadata for inspection/debugging.
            #
            metadata[
                "search_text"
            ] = document.page_content

            vectors.append(
                {
                    "id":
                        document.metadata[
                            "question_id"
                        ],

                    "values":
                        embedding,

                    "metadata":
                        metadata,
                }
            )

        index.upsert(
            vectors=vectors,
            namespace=NAMESPACE,
        )

        end = min(
            start + BATCH_SIZE,
            total,
        )

        print(
            f"Upserted "
            f"{end}/{total}"
        )

    #
    # Pinecone is eventually consistent,
    # so stats may take a short time to update.
    #
    print()
    print(
        "Waiting briefly for Pinecone "
        "indexing..."
    )

    time.sleep(5)

    stats = (
        index.describe_index_stats()
    )

    print()
    print(
        "Ingestion complete."
    )

    print(
        f"Index     : "
        f"{INDEX_NAME}"
    )

    print(
        f"Namespace : "
        f"{NAMESPACE}"
    )

    print()
    print(
        "Index stats:"
    )

    print(
        stats
    )


if __name__ == "__main__":
    main()