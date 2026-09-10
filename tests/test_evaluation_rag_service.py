import contextlib
import io
import unittest
from unittest.mock import patch

from src.evaluation_rag import service
from scripts import test_evaluation_rag_service as smoke


class EvaluationRAGServiceTests(unittest.TestCase):
    def test_convenience_function_returns_context_and_reuses_service(self):
        with patch.object(service, "_default_service", None), patch.object(
            service, "EvaluationDenseRetriever", autospec=True
        ) as retriever_class:
            retriever_class.return_value.retrieve.return_value = [{
                "evaluation_id": "EVAL-TEST", "rank": 1, "score": 0.9,
                "search_text": "Evidence text",
            }]
            result = service.retrieve_evaluation_context(" Question ", "Answer", "rag")
            self.assertEqual(result["retrieved_knowledge"], [{
                "evaluation_id": "EVAL-TEST", "rank": 1, "score": 0.9,
                "content": "Evidence text",
            }])
            retriever_class.return_value.retrieve.assert_called_once_with(
                query="Question", competency="rag", k=5,
            )
            service.retrieve_evaluation_context("Question", "Other answer", "rag")
            retriever_class.assert_called_once_with(k=5)

    def test_smoke_script_reads_context_evidence(self):
        with patch.object(smoke, "retrieve_evaluation_context", return_value={
            "retrieved_knowledge": [{"rank": 1, "evaluation_id": "EVAL-TEST", "score": 0.9}]
        }), contextlib.redirect_stdout(io.StringIO()) as output:
            smoke.main()
        self.assertIn("1. EVAL-TEST score=0.9000", output.getvalue())


if __name__ == "__main__":
    unittest.main()
