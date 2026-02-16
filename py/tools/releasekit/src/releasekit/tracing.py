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

"""OpenTelemetry tracing for releasekit pipelines.

Provides distributed tracing for release operations. Tracing is always
available but only emits real spans when a ``TracerProvider`` is
configured (e.g. via CLI flags or environment variables). Without
configuration, the default OTel no-op provider silently discards spans.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ Plain-English                                  │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Tracer              │ A factory that creates spans. One per module. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Span                │ A timed operation with a name, attributes,    │
    │                     │ and parent/child relationships.               │
    └─────────────────────┴────────────────────────────────────────────────┘

Setup::

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

import asyncio
import functools
import inspect
from typing import Any

from opentelemetry import trace as _otel_trace

# Module-level cache of tracers.
_TRACERS: dict[str, Any] = {}

# The instrumentation library name used for all releasekit spans.
_INSTRUMENTATION_NAME = 'releasekit'


def get_tracer(name: str = _INSTRUMENTATION_NAME) -> _otel_trace.Tracer:
    """Return a tracer instance.

    Returns a real OTel tracer. If no ``TracerProvider`` has been
    configured, the default OTel no-op provider is used (spans are
    silently discarded).

    Args:
        name: Tracer name (typically ``__name__`` of the calling module).

    Returns:
        An OpenTelemetry tracer.
    """
    if name in _TRACERS:
        return _TRACERS[name]

    tracer = _otel_trace.get_tracer(name)
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
    return inspect.iscoroutinefunction(fn) or (
        hasattr(fn, '__wrapped__') and asyncio.iscoroutinefunction(fn.__wrapped__)
    )


__all__ = [
    'get_tracer',
    'span',
]
