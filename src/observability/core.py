"""Context-local correlation, bounded sanitization, JSON logs and optional export."""

import inspect
import json
import logging
import math
import os
import re
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4


_context = ContextVar("observability_context", default=None)
_span_id = ContextVar("observability_span", default=None)
_remote = ContextVar("observability_remote", default=None)
_logger = logging.getLogger("interviewgap.telemetry")
_logger.addHandler(logging.NullHandler())
_logger.propagate = False
_export_enabled = False
_project = "interviewgap-ai"

_PRIVATE = {
    "question", "query", "answer", "candidateanswer", "resume", "resumetext",
    "content", "searchtext", "text", "prompt", "messages", "input", "inputs",
    "output", "outputs", "body", "headers", "email", "phone", "address",
    "name", "fullname", "candidatename", "candidateid", "password", "secret",
    "authorization", "cookie", "cookies", "token", "accesstoken", "refreshtoken",
    "apikey", "credentials", "exception", "errormessage", "stacktrace",
}
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_SECRET = re.compile(r"(?i)(?:bearer\s+\S+|(?:sk-|lsv2_|ghp_|github_pat_)[A-Za-z0-9_-]+)")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)")
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")


def sanitize(value, *, _depth=0):
    """Copy JSON-like metadata, omitting payloads and redacting common identifiers.

    Never call repr/str on arbitrary objects. Bounds cover cycles and large data.
    This is metadata sanitization, not a general-purpose free-text PII detector.
    """
    if _depth > 6:
        return "[TRUNCATED]"
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        if _UUID.fullmatch(value):
            return value
        value = _SECRET.sub("[REDACTED]", value)
        value = _EMAIL.sub("[REDACTED]", value)
        value = _PHONE.sub("[REDACTED]", value)
        return value[:2000]
    if isinstance(value, dict):
        result = {}
        for key, item in list(value.items())[:100]:
            if not isinstance(key, str):
                continue
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            private = normalized in _PRIVATE or normalized.endswith("token") or any(
                word in normalized for word in ("apikey", "password", "secret", "authorization")
            )
            result[sanitize(key)] = "[REDACTED]" if private else sanitize(item, _depth=_depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize(item, _depth=_depth + 1) for item in value[:100]]
    return "[OMITTED]"


def current_context():
    """Return a copy so callers cannot mutate another span's correlation IDs."""
    return dict(_context.get() or {})


def _identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("Correlation IDs must be opaque letters, digits, underscores or hyphens (1–128 characters).")
    return value


@contextmanager
def request_context(*, request_id=None, interview_id=None, question_id=None):
    """Start a fresh operation; link operations with opaque interview/question IDs.

    ContextVars isolate asyncio tasks. Pass IDs explicitly across processes or
    manually created threads; do not use names/email addresses as identifiers.
    """
    ids = {"trace_id": str(uuid4()), "request_id": _identifier(request_id) if request_id is not None else str(uuid4())}
    for key, value in (("interview_id", interview_id), ("question_id", question_id)):
        if value is not None:
            ids[key] = _identifier(value)
    token = _context.set(ids)
    span_token = _span_id.set(None)
    remote_token = _remote.set(None)
    try:
        yield dict(ids)
    finally:
        _remote.reset(remote_token)
        _span_id.reset(span_token)
        _context.reset(token)


class _JSONFormatter(logging.Formatter):
    def format(self, record):
        # Only our structured event is serialized; no raw message or traceback.
        return json.dumps(record.telemetry, ensure_ascii=False, allow_nan=False)


class _SafeHandler(logging.StreamHandler):
    def handleError(self, record):
        # Logging failures must not print the original record or break requests.
        pass


def configure_observability(*, stream=None, level="INFO", tracing_enabled=None, project=None):
    """Configure once at application startup, after loading environment settings.

    Owns only interviewgap.telemetry. Repeated calls replace our handler.
    Export is opt-in through LANGSMITH_TRACING=true or tracing_enabled=True.
    """
    global _export_enabled, _project
    handler = _SafeHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(_JSONFormatter())
    _logger.setLevel(level.upper())
    for old in list(_logger.handlers):
        _logger.removeHandler(old)
        old.close()
    _logger.addHandler(handler)
    _project = project or os.getenv("LANGSMITH_PROJECT") or "interviewgap-ai"
    _export_enabled = (
        os.getenv("LANGSMITH_TRACING", "").lower() == "true"
        if tracing_enabled is None else bool(tracing_enabled)
    )


def log_event(event, *, level="INFO", **attributes):
    """Emit a static event name plus sanitized metadata, never free-text payloads."""
    try:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(), "event": sanitize(event),
            **current_context(), "span_id": _span_id.get(),
            "attributes": sanitize(attributes),
        }
        _logger.log(getattr(logging, level.upper(), logging.INFO), event, extra={"telemetry": record})
    except Exception:
        pass


def flush_telemetry(timeout=2.0):
    """Best-effort bounded export flush at application/worker shutdown."""
    if not _export_enabled:
        return
    try:
        from langsmith.run_trees import get_cached_client

        get_cached_client().flush(timeout=timeout)
    except Exception as exc:
        log_event("telemetry.export_failed", level="WARNING", error_type=type(exc).__name__)


def _start_remote(name, span_id, attributes):
    if not _export_enabled:
        return None
    try:
        from langsmith.run_trees import RunTree

        options = dict(
            name=sanitize(name), run_type="chain", inputs={},
            extra={"metadata": {**sanitize(attributes), **current_context()}},
        )
        parent = _remote.get()
        run = parent.create_child(run_id=span_id, **options) if parent else RunTree(id=span_id, project_name=_project, **options)
        run.post()
        return run
    except Exception as exc:
        log_event("telemetry.export_failed", level="WARNING", error_type=type(exc).__name__)
        return None


class Span:
    def __init__(self):
        self.attributes = {}

    def set_attributes(self, **attributes):
        self.attributes.update(sanitize(attributes))


@contextmanager
def trace_span(name, **attributes):
    """Trace an operation without automatically capturing arguments or results."""
    if _context.get() is None:
        with request_context():
            with trace_span(name, **attributes) as span:
                yield span
        return
    parent_id = _span_id.get()
    span_id = str(uuid4()) if parent_id else current_context()["trace_id"]
    token = _span_id.set(span_id)
    run = _start_remote(name, span_id, attributes)
    remote_token = _remote.set(run)
    span = Span()
    span.set_attributes(**attributes)
    started = time.perf_counter()
    error_type = None
    log_event("span.started", operation=name, parent_span_id=parent_id, details=span.attributes)
    try:
        yield span
    except BaseException as exc:
        error_type = type(exc).__name__
        raise
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        log_event(
            "span.finished", level="ERROR" if error_type else "INFO",
            operation=name, parent_span_id=parent_id, status="error" if error_type else "ok",
            duration_ms=duration_ms, error_type=error_type, details=span.attributes,
        )
        if run is not None:
            try:
                run.end(outputs={"metadata": sanitize(span.attributes)}, error=error_type)
                run.patch()
            except Exception as exc:
                log_event("telemetry.export_failed", level="WARNING", error_type=type(exc).__name__)
        _remote.reset(remote_token)
        _span_id.reset(token)


def traced(name):
    """Decorator for synchronous and coroutine functions; no payload capture."""
    def decorate(function):
        if inspect.iscoroutinefunction(function):
            @wraps(function)
            async def async_wrapper(*args, **kwargs):
                with trace_span(name):
                    return await function(*args, **kwargs)
            return async_wrapper

        @wraps(function)
        def wrapper(*args, **kwargs):
            with trace_span(name):
                return function(*args, **kwargs)
        return wrapper
    return decorate
