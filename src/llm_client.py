"""
Shared OpenAI-compatible client construction, selectable by provider.

DeepSeek's API is OpenAI-compatible and reachable through the same openai
SDK; only the base URL, key, and default model differ. LLM_PROVIDER picks
between them so a stage's provider is a config change, not a code change.
"""

import os

from openai import OpenAI


def build_client(default_openai_model: str, *, provider: str | None = None) -> tuple[OpenAI, str]:
    """
    Return a client for the configured provider and its default model.

    max_retries=0 on both: src.llm_retry.call_with_retry owns retry
    decisions, so a permanent failure (no credit remaining, a bad key)
    fails immediately instead of paying the SDK's own backoff first.

    provider overrides LLM_PROVIDER for this one call. Every stage that
    scores or generates uses the env var alone; a caller that must not share
    a vendor with another stage (see src.evaluation.online_judge) passes
    provider explicitly instead of relying on global config.
    """

    provider = (provider or os.getenv("LLM_PROVIDER", "openai")).strip().lower()

    if provider == "deepseek":
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            max_retries=0,
        )
        return client, os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    if provider != "openai":
        raise ValueError(
            f"Unknown LLM_PROVIDER: {provider!r}. Use 'openai' or 'deepseek'."
        )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), max_retries=0)
    return client, default_openai_model


__all__ = ["build_client"]
