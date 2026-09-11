"""
Shared retry policy for OpenAI-compatible calls: skip retries a resend can
never fix, and retry the one kind of failure a resend reliably does fix.

The SDK's own max_retries cannot tell a transient 429 (retry helps) from a
429 that means the account has no credit left (retry never helps, only
delays the same failure). Each stage's client sets max_retries=0 and routes
its call through call_with_retry, which makes that distinction explicit.

It also covers a failure the SDK does not retry at all: on a provider whose
structured-output support is looser than OpenAI's own (observed on
DeepSeek), the model occasionally returns text that does not match the
requested schema - once, notably, the JSON *schema* itself instead of filled
data. responses.parse raises this as a pydantic ValidationError from inside
the SDK call, before any application code sees a response. It is a
generation flake, not a schema or prompt bug: the same call with identical
input succeeded on every retry observed. That makes it worth one resend,
unlike an InterviewPlan failing its own cross-field arithmetic check, which
is a distinct, deliberately un-retried-here validator (see
src.planning.interview_planner's own repair loop).
"""

import random
import time
from typing import Callable, TypeVar

import openai
import pydantic


T = TypeVar("T")

# Codes returned inside a 429 body that describe account/billing state, not
# transient load. No number of retries changes a zero credit balance; every
# retry against one of these just pays the backoff delay to reach the same
# permanent failure, which is what looked like the pipeline hanging.
_NON_RETRYABLE_RATE_LIMIT_CODES = {
    "insufficient_quota",
    "credit_balance_exhausted",
    "billing_hard_limit_reached",
}


def _is_retryable(error: BaseException) -> bool:
    """A later attempt could plausibly succeed."""

    if isinstance(error, openai.RateLimitError):
        code = None
        body = getattr(error, "body", None)
        if isinstance(body, dict):
            code = (body.get("error") or {}).get("code")
        return code not in _NON_RETRYABLE_RATE_LIMIT_CODES
    if isinstance(error, pydantic.ValidationError):
        # Raised inside responses.parse itself when the model's output does
        # not match text_format - a generation flake on a provider with
        # looser structured-output enforcement, not an application error.
        return True
    return isinstance(
        error,
        (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError),
    )


def call_with_retry(
    operation: Callable[[], T],
    *,
    max_retries: int = 4,
    base_delay: float = 0.5,
) -> T:
    """
    Run one OpenAI call, retrying only failures another attempt could fix.

    A transient overload or dropped connection is worth retrying with
    backoff. A quota-exhausted account is not: it fails the same way every
    time, so this raises immediately instead of spending max_retries worth
    of backoff to reach the same answer.
    """

    attempt = 0
    while True:
        try:
            return operation()
        except Exception as error:
            if attempt >= max_retries or not _is_retryable(error):
                raise
            delay = base_delay * (2**attempt) + random.uniform(0, base_delay)
            time.sleep(delay)
            attempt += 1


__all__ = ["call_with_retry"]
