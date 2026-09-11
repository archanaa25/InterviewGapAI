import unittest
from unittest.mock import patch

import httpx
import openai

from src.llm_retry import call_with_retry


def _rate_limit_error(code: str | None) -> openai.RateLimitError:
    """Build the same exception shape the SDK raises for a 429 response."""

    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429, request=request, json={"error": {"code": code}})
    return openai.RateLimitError(
        message="rate limited", response=response, body=response.json()
    )


class CallWithRetryTests(unittest.TestCase):
    def test_returns_the_result_on_the_first_success(self):
        self.assertEqual(call_with_retry(lambda: 42), 42)

    @patch("src.llm_retry.time.sleep")
    def test_retries_a_transient_internal_server_error(self, sleep):
        attempts = []

        def operation():
            attempts.append(1)
            if len(attempts) < 3:
                request = httpx.Request("POST", "https://api.openai.com/v1/responses")
                response = httpx.Response(500, request=request, json={"error": {}})
                raise openai.InternalServerError(
                    message="overloaded", response=response, body={}
                )
            return "ok"

        result = call_with_retry(operation, max_retries=4, base_delay=0.01)

        self.assertEqual(result, "ok")
        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("src.llm_retry.time.sleep")
    def test_does_not_retry_a_quota_exhausted_account(self, sleep):
        """The exact failure mode from the live repro: insufficient_quota.

        A retry can never fix a zero credit balance. Retrying anyway is what
        made this failure look like the pipeline hanging before it errored.
        """

        attempts = []

        def operation():
            attempts.append(1)
            raise _rate_limit_error("insufficient_quota")

        with self.assertRaises(openai.RateLimitError):
            call_with_retry(operation, max_retries=4, base_delay=0.01)

        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    @patch("src.llm_retry.time.sleep")
    def test_retries_an_ordinary_rate_limit_without_a_billing_code(self, sleep):
        attempts = []

        def operation():
            attempts.append(1)
            if len(attempts) < 2:
                raise _rate_limit_error(None)
            return "ok"

        result = call_with_retry(operation, max_retries=4, base_delay=0.01)

        self.assertEqual(result, "ok")
        self.assertEqual(len(attempts), 2)

    @patch("src.llm_retry.time.sleep")
    def test_gives_up_after_max_retries(self, sleep):
        def operation():
            request = httpx.Request("POST", "https://api.openai.com/v1/responses")
            response = httpx.Response(500, request=request, json={"error": {}})
            raise openai.InternalServerError(message="overloaded", response=response, body={})

        with self.assertRaises(openai.InternalServerError):
            call_with_retry(operation, max_retries=2, base_delay=0.01)

        self.assertEqual(sleep.call_count, 2)

    def test_does_not_retry_an_unrelated_application_error(self):
        attempts = []

        def operation():
            attempts.append(1)
            raise ValueError("not an API failure")

        with self.assertRaises(ValueError):
            call_with_retry(operation, max_retries=4)

        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
