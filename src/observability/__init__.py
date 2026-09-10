"""Shared, opt-in application telemetry. No configuration occurs on import."""

from .core import (
    configure_observability,
    current_context,
    flush_telemetry,
    log_event,
    request_context,
    sanitize,
    trace_span,
    traced,
)

__all__ = [
    "configure_observability", "current_context", "flush_telemetry", "log_event",
    "request_context", "sanitize", "trace_span", "traced",
]
