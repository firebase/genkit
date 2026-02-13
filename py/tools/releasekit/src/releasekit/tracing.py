# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Optional OpenTelemetry tracing for releasekit pipelines.

Wraps the OpenTelemetry API so that tracing is **completely optional**:
if ``opentelemetry-api`` is not installed, all operations gracefully
degrade to no-ops. This means releasekit never requires OTel as a
hard dependency.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Tracer              │ A factory that creates spans. One per module. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Span                │ A timed operation with a name, attributes,    │
    │                     │ and parent/child relationships.               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ NoOpSpan            │ A do-nothing span used when OTel is absent.   │
    └─────────────────────┴────────────────────────────────────────────────┘

Setup (optional)::

    # Install the optional dependency:
    pip install opentelemetry-api opentelemetry-sdk

    # In your entrypoint, configure the SDK before calling releasekit:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    # Now all releasekit operations emit spans automatically.

Usage in releasekit modules::

    from releasekit.tracing import get_tracer, span

    tracer = get_tracer(__name__)

    # Context manager style:
    with tracer.start_as_current_span('compute_bumps') as s:
        s.set_attribute('package_count', len(packages))
        ...


    # Or use the convenience decorator:
    @span('publish_package')
    async def publish(name: str) -> None: ...
"""

from __future__ import annotations

import functools
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

# Try to import OpenTelemetry. If not installed, use no-op fallbacks.
_OTEL_AVAILABLE = False
try:
    from opentelemetry import trace as _otel_trace

    _OTEL_AVAILABLE = True
except ImportError:
    _otel_trace = None  # type: ignore[assignment]


class _NoOpSpan:
    """A do-nothing span for when OpenTelemetry is not installed."""

    def set_attribute(self, key: str, value: Any) -> None:  # noqa: ANN401
        """No-op."""

    def set_status(self, status: Any, description: str | None = None) -> None:  # noqa: ANN401
        """No-op."""

    def record_exception(self, exception: BaseException) -> None:
        """No-op."""

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """No-op."""

    def end(self) -> None:
        """No-op."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: object) -> None:
        pass


_NO_OP_SPAN = _NoOpSpan()


class _NoOpTracer:
    """A do-nothing tracer for when OpenTelemetry is not installed."""

    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> Generator[_NoOpSpan, None, None]:
        """Yield a no-op span."""
        yield _NO_OP_SPAN

    def start_span(self, name: str, **kwargs: Any) -> _NoOpSpan:  # noqa: ANN401
        """Return a no-op span."""
        return _NO_OP_SPAN


_NO_OP_TRACER = _NoOpTracer()

# Module-level cache of tracers.
_TRACERS: dict[str, Any] = {}

# The instrumentation library name used for all releasekit spans.
_INSTRUMENTATION_NAME = 'releasekit'


def is_available() -> bool:
    """Return True if OpenTelemetry is installed and configured.

    Returns:
        ``True`` if ``opentelemetry-api`` is importable.
    """
    return _OTEL_AVAILABLE


def get_tracer(name: str = _INSTRUMENTATION_NAME) -> Any:  # noqa: ANN401
    """Return a tracer instance.

    If OpenTelemetry is installed, returns a real OTel tracer.
    Otherwise, returns a :class:`_NoOpTracer` that silently ignores
    all span operations.

    Args:
        name: Tracer name (typically ``__name__`` of the calling module).

    Returns:
        A tracer (real or no-op).
    """
    if name in _TRACERS:
        return _TRACERS[name]

    if _OTEL_AVAILABLE and _otel_trace is not None:
        tracer = _otel_trace.get_tracer(name)
    else:
        tracer = _NO_OP_TRACER

    _TRACERS[name] = tracer
    return tracer


def span(
    name: str,
    *,
    tracer_name: str = _INSTRUMENTATION_NAME,
    attributes: dict[str, Any] | None = None,
) -> Any:  # noqa: ANN401
    """Decorator that wraps a function in an OTel span.

    Works with both sync and async functions. If OTel is not installed,
    the decorator is a transparent pass-through with zero overhead.

    Args:
        name: Span name.
        tracer_name: Tracer to use (default: ``"releasekit"``).
        attributes: Optional static attributes to set on the span.

    Returns:
        A decorator.

    Example::

        @span('publish_package')
        async def publish(name: str) -> None: ...


        @span('compute_graph', attributes={'algo': 'bfs'})
        def build_graph(packages: list) -> Graph: ...
    """

    def decorator(fn: Any) -> Any:  # noqa: ANN401
        if not _OTEL_AVAILABLE:
            # Zero-overhead pass-through when OTel is absent.
            return fn

        tracer = get_tracer(tracer_name)

        if _is_coroutine_function(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
                with tracer.start_as_current_span(name) as s:
                    if attributes:
                        for k, v in attributes.items():
                            s.set_attribute(k, v)
                    try:
                        return await fn(*args, **kwargs)
                    except Exception as exc:
                        s.record_exception(exc)
                        raise

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            with tracer.start_as_current_span(name) as s:
                if attributes:
                    for k, v in attributes.items():
                        s.set_attribute(k, v)
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    s.record_exception(exc)
                    raise

        return sync_wrapper

    return decorator


def _is_coroutine_function(fn: Any) -> bool:  # noqa: ANN401
    """Check if a function is a coroutine function.

    Handles both native ``async def`` and functools-wrapped coroutines.
    """
    import asyncio
    import inspect

    return inspect.iscoroutinefunction(fn) or (
        hasattr(fn, '__wrapped__') and asyncio.iscoroutinefunction(fn.__wrapped__)
    )


__all__ = [
    'get_tracer',
    'is_available',
    'span',
]
