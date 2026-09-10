"""
InterviewGap AI - Metadata-Filtered Dense Question Retriever

E4A: competency
E4B: competency + difficulty
E4C: competency + sub_competency + difficulty
"""


from src.retrieval.dense_retriever import QuestionDenseRetriever

class MetadataFilteredDenseRetriever:
    VALID_FILTER_MODES = {
        "competency",
        "competency_difficulty",
        "full",
    }

    def __init__(self, k=5, filter_mode="competency"):
        if filter_mode not in self.VALID_FILTER_MODES:
            raise ValueError(
                f"Invalid filter_mode '{filter_mode}'. "
                f"Choose from: {sorted(self.VALID_FILTER_MODES)}"
            )

        self.k = k
        self.filter_mode = filter_mode
        # The evaluation runner uses this flag to pass the golden record as
        # metadata alongside the natural-language retrieval query.
        self.uses_metadata = True
        self.dense = QuestionDenseRetriever(k=k)

    def _build_filters(self, metadata):
        if not metadata:
            return None

        filters = {}

        # Translate caller field names into the metadata keys stored in Pinecone.
        # Omitted values leave that dimension unconstrained.
        competency = metadata.get("expected_competency")
        difficulty = metadata.get("difficulty_target")
        sub_competency = metadata.get("expected_sub_competency")

        # E4A, E4B, E4C
        if competency is not None:
            filters["competency"] = competency

        # E4B, E4C: difficulty narrows the candidate pool before semantic ranking.
        # competency_difficulty is the selected MVP mode; callers choose it explicitly.
        if (
            self.filter_mode in {"competency_difficulty", "full"}
            and difficulty is not None
        ):
            filters["difficulty"] = difficulty

        # E4C only
        if (
            self.filter_mode == "full"
            and sub_competency is not None
        ):
            filters["sub_competency"] = sub_competency

        # None preserves the base retriever's unfiltered search behavior when
        # no usable constraints were supplied.
        return filters or None

    def search(self, query, k=None, metadata=None):
        if k is None:
            k = self.k

        filters = self._build_filters(metadata)

        # The shared dense retriever owns embedding, Pinecone access, and
        # result formatting; this wrapper only selects metadata constraints.
        return self.dense.search(
            query,
            k=k,
            filters=filters,
        )


def main():
    query = (
        "The steps in my process are known in advance and rarely change. "
        "Should the model really be deciding what happens next?"
    )

    metadata = {
        "expected_competency": "agentic_ai",
        "expected_sub_competency": "agent_fundamentals",
        "difficulty_target": "intermediate",
    }

    for mode in [
        "competency",
        "competency_difficulty",
        "full",
    ]:
        print()
        print("=" * 80)
        print(f"FILTER MODE: {mode}")
        print("=" * 80)

        retriever = MetadataFilteredDenseRetriever(
            k=5,
            filter_mode=mode,
        )

        results = retriever.search(
            query,
            k=5,
            metadata=metadata,
        )

        for result in results:
            marker = (
                " <-- EXPECTED"
                if result["question_id"] == "AGENT-FUND-INT-001"
                else ""
            )

            print(
                f"{result['rank']}. "
                f"{result['question_id']} "
                f"score={result['score']:.4f}"
                f"{marker}"
            )


if __name__ == "__main__":
    main()
