from __future__ import annotations

import hashlib
import os
from contextlib import nullcontext
from typing import Any

from dotenv import load_dotenv

from .pii import scrub_text

load_dotenv()

if os.getenv("LANGFUSE_BASE_URL") and not os.getenv("LANGFUSE_HOST"):
    os.environ["LANGFUSE_HOST"] = os.environ["LANGFUSE_BASE_URL"]
if os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
    os.environ["LANGFUSE_BASE_URL"] = os.environ["LANGFUSE_HOST"]

try:
    from langfuse import Langfuse
    from langfuse import get_client as _get_client
    from langfuse import observe as _observe
    from langfuse import propagate_attributes as _propagate_attributes
except Exception:  # pragma: no cover
    Langfuse = None  # type: ignore[assignment]
    _get_client = None
    _observe = None
    _propagate_attributes = None


class _NoopObservation:
    trace_id = ""
    id = ""

    def update(self, **_: Any) -> "_NoopObservation":
        return self

    def end(self) -> None:
        return None

    def set_trace_io(self, **_: Any) -> None:
        return None

    def start_as_current_observation(self, **_: Any):
        return nullcontext(_NoopObservation())


class _NoopLangfuse:
    def start_as_current_observation(self, **_: Any):
        return nullcontext(_NoopObservation())

    def update_current_span(self, **_: Any) -> None:
        return None

    def update_current_generation(self, **_: Any) -> None:
        return None

    def set_current_trace_io(self, **_: Any) -> None:
        return None

    def score_current_trace(self, **_: Any) -> None:
        return None

    def flush(self) -> None:
        return None

    def shutdown(self) -> None:
        return None

    def create_trace_id(self, seed: str | None = None) -> str:
        source = seed or "day13-observability-lab"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]


_client: Any | None = None


def mask_langfuse_data(data: Any, **_: Any) -> Any:
    if isinstance(data, str):
        return scrub_text(data)
    if isinstance(data, dict):
        return {key: mask_langfuse_data(value) for key, value in data.items()}
    if isinstance(data, list):
        return [mask_langfuse_data(item) for item in data]
    if isinstance(data, tuple):
        return tuple(mask_langfuse_data(item) for item in data)
    return data


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def get_langfuse_client() -> Any:
    global _client
    if _client is not None:
        return _client

    if not tracing_enabled() or Langfuse is None or _get_client is None:
        _client = _NoopLangfuse()
        return _client

    _client = Langfuse(mask=mask_langfuse_data)
    return _client


def observe(*args: Any, **kwargs: Any):
    if tracing_enabled() and _observe is not None:
        get_langfuse_client()
        return _observe(*args, **kwargs)

    def decorator(func):
        return func

    if args and callable(args[0]) and not kwargs:
        return args[0]
    return decorator


def propagate_trace_attributes(**kwargs: Any):
    if tracing_enabled() and _propagate_attributes is not None:
        get_langfuse_client()
        return _propagate_attributes(**kwargs)
    return nullcontext()


def flush_traces() -> None:
    get_langfuse_client().flush()


def shutdown_traces() -> None:
    client = get_langfuse_client()
    shutdown = getattr(client, "shutdown", None)
    if callable(shutdown):
        shutdown()
    else:
        client.flush()
