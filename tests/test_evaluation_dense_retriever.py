import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.evaluation_rag.dense_retriever import EvaluationDenseRetriever


class EvaluationDenseRetrieverTests(unittest.TestCase):
    def setUp(self):
        # Exercise the real retrieval methods without constructing live clients.
        self.retriever = EvaluationDenseRetriever.__new__(EvaluationDenseRetriever)
        self.retriever.k = 9
        self.retriever.namespace = "evaluation-v1"
        self.retriever._embed_query = Mock(return_value=[0.1, 0.2])
        self.retriever.index = Mock()
        self.retriever.index.query.return_value = SimpleNamespace(matches=[
            SimpleNamespace(
                id="EVAL-RAG-CHUNK", score=0.9,
                metadata={"competency": "rag", "search_text": "Chunk evidence"},
            ),
        ])

    def test_agent_contract_and_default_filter(self):
        results = self.retriever.retrieve("Chunk size?", "rag")
        self.retriever._embed_query.assert_called_once_with("Chunk size?")
        self.retriever.index.query.assert_called_once_with(
            namespace="evaluation-v1", vector=[0.1, 0.2], top_k=5,
            include_metadata=True, filter={"competency": "rag"},
        )
        self.assertEqual(results, [{
            "evaluation_id": "EVAL-RAG-CHUNK", "rank": 1, "score": 0.9,
            "competency": "rag", "sub_competency": None, "topic": None,
            "search_text": "Chunk evidence",
        }])

    def test_empty_results_do_not_trigger_unfiltered_fallback(self):
        self.retriever.index.query.return_value = SimpleNamespace(matches=[])
        self.assertEqual(self.retriever.retrieve("Question", "rag", k=3), [])
        self.assertEqual(self.retriever.index.query.call_count, 1)
        self.assertEqual(self.retriever.index.query.call_args.kwargs["top_k"], 3)
        self.assertEqual(self.retriever.index.query.call_args.kwargs["filter"], {"competency": "rag"})

    def test_invalid_inputs_fail_before_service_calls(self):
        for query, competency, k in [
            (" ", "rag", 5), (None, "rag", 5), ("Q", "", 5),
            ("Q", None, 5), ("Q", "rag", 0), ("Q", "rag", -1),
            ("Q", "rag", True), ("Q", "rag", 1.5),
        ]:
            with self.subTest(query=query, competency=competency, k=k):
                with self.assertRaises(ValueError):
                    self.retriever.retrieve(query, competency, k)
        self.retriever._embed_query.assert_not_called()
        self.retriever.index.query.assert_not_called()

    def test_service_failure_propagates(self):
        self.retriever.index.query.side_effect = RuntimeError("service unavailable")
        with self.assertRaisesRegex(RuntimeError, "service unavailable"):
            self.retriever.retrieve("Question", "rag")

    def test_legacy_unfiltered_search_remains_available(self):
        self.retriever.search("Question")
        options = self.retriever.index.query.call_args.kwargs
        self.assertNotIn("filter", options)
        self.assertEqual(options["top_k"], 9)

    def test_empty_namespace_uses_mvp_default(self):
        with patch.dict("os.environ", {
            "OPENAI_API_KEY": "test", "PINECONE_API_KEY": "test",
            "PINECONE_EVALUATION_NAMESPACE": "",
        }), patch("src.evaluation_rag.dense_retriever.OpenAI"), patch(
            "src.evaluation_rag.dense_retriever.Pinecone"
        ):
            self.assertEqual(EvaluationDenseRetriever().namespace, "evaluation-v1")


if __name__ == "__main__":
    unittest.main()
