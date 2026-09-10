import asyncio
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.observability import (
    configure_observability, current_context, flush_telemetry, log_event, request_context,
    sanitize, trace_span, traced,
)


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        configure_observability(stream=self.stream, tracing_enabled=False)

    def tearDown(self):
        configure_observability(stream=io.StringIO(), tracing_enabled=False)

    def records(self):
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_nested_spans_preserve_ids_and_restore_context(self):
        with request_context(request_id="request-1", interview_id="interview-1") as ids:
            with trace_span("parent"):
                with trace_span("child"):
                    log_event("retrieval.results", result_count=5)
        self.assertEqual(current_context(), {})
        records = self.records()
        self.assertTrue(all(r["trace_id"] == ids["trace_id"] for r in records))
        starts = [r for r in records if r["event"] == "span.started"]
        self.assertEqual(starts[1]["attributes"]["parent_span_id"], starts[0]["span_id"])
        self.assertNotEqual(starts[0]["span_id"], starts[1]["span_id"])

    def test_redaction_and_no_arbitrary_repr(self):
        class SecretObject:
            def __repr__(self):
                raise AssertionError("must not inspect objects")
        payload = {"nested": {"OPENAI_API_KEY": "hidden-key", "candidate_answer": "private answer"},
                   "note": "person@example.com Bearer abc123 +971 50 123 4567",
                   "object": SecretObject(), "score": float("nan")}
        log_event("test.redaction", payload=payload)
        text = self.stream.getvalue()
        for secret in ("hidden-key", "private answer", "person@example.com", "abc123", "+971 50 123 4567"):
            self.assertNotIn(secret, text)
        self.assertIsNone(self.records()[0]["attributes"]["payload"]["score"])
        self.assertEqual(payload["nested"]["OPENAI_API_KEY"], "hidden-key")
        cycle = {}; cycle["cycle"] = cycle
        self.assertIn("TRUNCATED", json.dumps(sanitize(cycle)))

    def test_exception_propagates_without_message_or_payload_capture(self):
        error = RuntimeError("private candidate data")
        @traced("failure")
        def fail(answer):
            raise error
        with self.assertRaises(RuntimeError) as caught:
            fail("secret answer")
        self.assertIs(caught.exception, error)
        self.assertEqual(current_context(), {})
        text = self.stream.getvalue()
        self.assertNotIn("private candidate data", text)
        self.assertNotIn("secret answer", text)
        self.assertEqual(self.records()[-1]["attributes"]["error_type"], "RuntimeError")
        self.assertEqual(self.records()[-1]["attributes"]["status"], "error")

    def test_concurrent_async_requests_are_isolated(self):
        @traced("async.operation")
        async def operation():
            await asyncio.sleep(0)
            log_event("async.result")
            return current_context()["request_id"]
        async def request(identifier):
            with request_context(request_id=identifier):
                return await operation()
        async def run():
            return await asyncio.gather(request("one"), request("two"))
        self.assertEqual(asyncio.run(run()), ["one", "two"])
        results = [r for r in self.records() if r["event"] == "async.result"]
        self.assertEqual(len({r["trace_id"] for r in results}), 2)

    def test_reconfigure_does_not_duplicate_logs(self):
        configure_observability(stream=self.stream, tracing_enabled=False)
        log_event("once")
        self.assertEqual(len(self.records()), 1)

    def test_bad_sink_does_not_break_application(self):
        class BrokenStream:
            def write(self, value):
                raise OSError("sink unavailable")
            def flush(self):
                pass
        configure_observability(stream=BrokenStream(), tracing_enabled=False)
        with trace_span("operation"):
            log_event("event")
        self.assertEqual(current_context(), {})

    def test_export_is_disabled_by_default(self):
        with patch("langsmith.run_trees.RunTree") as run:
            with trace_span("local"):
                pass
        run.assert_not_called()

    def test_real_run_tree_nesting_and_sanitized_export(self):
        from langsmith.run_trees import RunTree
        posted = []
        configure_observability(stream=self.stream, tracing_enabled=True)
        # Exercise real SDK construction and child signatures; block all exports.
        with patch.object(RunTree, "post", lambda run: posted.append(run)), patch.object(RunTree, "patch"):
            with trace_span("parent", api_key="private-key"):
                with trace_span("child") as span:
                    span.set_attributes(candidate_answer="private answer", result_count=3)
        self.assertEqual(len(posted), 2)
        self.assertEqual(posted[1].parent_run_id, posted[0].id)
        self.assertEqual(str(posted[0].id), self.records()[0]["trace_id"])
        self.assertNotIn("private-key", json.dumps(posted[0].extra))
        self.assertNotIn("private answer", json.dumps(posted[1].outputs))

    def test_export_failure_does_not_replace_business_error(self):
        configure_observability(stream=self.stream, tracing_enabled=True)
        with patch("langsmith.run_trees.RunTree", side_effect=RuntimeError("secret service response")):
            with self.assertRaisesRegex(ValueError, "business error"):
                with trace_span("operation"):
                    raise ValueError("business error")
        self.assertNotIn("secret service response", self.stream.getvalue())
        self.assertEqual(current_context(), {})

    def test_invalid_external_id_is_rejected(self):
        with self.assertRaises(ValueError):
            with request_context(request_id="person@example.com\ninjected"):
                pass

    def test_flush_uses_timeout_and_is_disabled_without_export(self):
        with patch("langsmith.run_trees.get_cached_client") as client:
            flush_telemetry()
            client.assert_not_called()
            configure_observability(stream=self.stream, tracing_enabled=True)
            flush_telemetry(timeout=0.5)
            client.return_value.flush.assert_called_once_with(timeout=0.5)

    def test_service_trace_omits_question_answer_and_evidence_text(self):
        from src.evaluation_rag import service
        with patch.object(service, "_default_service", None), patch.object(
            service, "EvaluationDenseRetriever", autospec=True
        ) as retriever:
            retriever.return_value.retrieve.return_value = [{
                "evaluation_id": "EVAL-RAG", "rank": 1, "score": 0.9,
                "search_text": "private evidence text",
            }]
            with request_context(interview_id="interview-1", question_id="question-1"):
                result = service.retrieve_evaluation_context("private question", "private answer", "rag")
        self.assertEqual(result["retrieved_knowledge"][0]["content"], "private evidence text")
        text = self.stream.getvalue()
        for private in ("private question", "private answer", "private evidence text"):
            self.assertNotIn(private, text)
        records = self.records()
        self.assertTrue(all(r["interview_id"] == "interview-1" for r in records))
        evidence = next(r for r in records if r["event"] == "evaluation_rag.results")
        self.assertEqual(evidence["attributes"]["evidence"][0]["evaluation_id"], "EVAL-RAG")

    def test_embedding_metadata_excludes_query_and_vector(self):
        from src.evaluation_rag.dense_retriever import EvaluationDenseRetriever
        retriever = EvaluationDenseRetriever.__new__(EvaluationDenseRetriever)
        retriever.embedding_model = "text-embedding-3-small"
        with patch.object(retriever, "openai_client", create=True) as client:
            client.embeddings.create.return_value = SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.123456])],
                usage=SimpleNamespace(total_tokens=12),
            )
            result = retriever._embed_query("private embedding query")
        self.assertEqual(result, [0.123456])
        text = self.stream.getvalue()
        self.assertNotIn("private embedding query", text)
        self.assertNotIn("0.123456", text)
        details = self.records()[-1]["attributes"]["details"]
        self.assertEqual(details["model"], "text-embedding-3-small")
        self.assertEqual(details["total_tokens"], 12)

    def test_async_cancellation_restores_context(self):
        @traced("cancelled.operation")
        async def operation():
            raise asyncio.CancelledError()
        async def run():
            with self.assertRaises(asyncio.CancelledError):
                await operation()
            self.assertEqual(current_context(), {})
        asyncio.run(run())
        self.assertEqual(self.records()[-1]["attributes"]["error_type"], "CancelledError")


if __name__ == "__main__":
    unittest.main()
