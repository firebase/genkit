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

"""OpenTelemetry instrumentation setup.

Configures OTLP trace export and instruments the ASGI app so that
every incoming HTTP request creates a trace span.  Supports FastAPI
(via ``opentelemetry-instrumentation-fastapi``), Litestar and Quart
(via ``opentelemetry-instrumentation-asgi``).

The resulting traces flow::

    HTTP request → ASGI middleware → Genkit flow → model call

Important: This module adds the OTLP exporter to Genkit's existing
``TracerProvider`` (via ``genkit.core.tracing.add_custom_exporter``)
instead of creating a competing provider.  This ensures both the
Genkit DevUI **and** an external collector (Jaeger, Grafana Tempo,
etc.) receive the same spans.  Without this, only one exporter would
work because OpenTelemetry's global ``set_tracer_provider()`` is
effectively a one-shot call.
"""

import fastapi
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter

from genkit.core.tracing import add_custom_exporter

logger = structlog.get_logger(__name__)


def _ensure_resource(service_name: str) -> None:
    """Ensure the global TracerProvider has a proper service name Resource.

    If no TracerProvider exists yet (e.g. running without the DevUI),
    create one with the ``SERVICE_NAME`` resource attribute so that
    traces appear with the correct service name in Jaeger / Tempo.

    If Genkit already created a provider (DevUI is active), this is a
    no-op — the provider is already registered.
    """
    current = trace.get_tracer_provider()
    if current is None or not isinstance(current, TracerProvider):
        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        logger.debug(
            "Created TracerProvider with service name",
            service_name=service_name,
        )


def _create_exporter(endpoint: str, protocol: str) -> SpanExporter:
    """Create an OTLP span exporter for the given protocol.

    Defaults to HTTP; falls back from gRPC to HTTP if the gRPC
    exporter package is not installed.
    """
    if protocol == "grpc":
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415 — conditional on OTEL protocol selection
                OTLPSpanExporter as GRPCSpanExporter,
            )

            return GRPCSpanExporter(endpoint=endpoint)
        except ImportError:
            logger.warning(
                "gRPC OTLP exporter not installed, falling back to HTTP. "
                "Install with: pip install opentelemetry-exporter-otlp-proto-grpc"
            )

    return HTTPSpanExporter(endpoint=f"{endpoint}/v1/traces")


def _instrument_fastapi(app: fastapi.FastAPI) -> None:
    """Instrument a FastAPI app with OpenTelemetry."""
    FastAPIInstrumentor.instrument_app(app)


def _instrument_asgi(app: object) -> None:
    """Instrument a Litestar or Quart app with generic ASGI middleware.

    Both Litestar and Quart expose ``asgi_handler`` as the inner ASGI
    callable. Wrapping it with the OTel middleware instruments all requests.
    """
    handler = getattr(app, "asgi_handler", None)
    if handler is None:
        logger.warning(
            "App has no asgi_handler attribute — skipping ASGI OTel instrumentation",
            app_type=type(app).__name__,
        )
        return
    setattr(app, "asgi_handler", OpenTelemetryMiddleware(handler))  # noqa: B010 — dynamic attribute on framework object; setattr avoids ty unresolved-attribute


def setup_otel_instrumentation(
    app: object,
    endpoint: str,
    protocol: str,
    service_name: str,
) -> None:
    """Configure OpenTelemetry tracing with OTLP export.

    Adds an OTLP exporter to Genkit's existing ``TracerProvider`` so
    that traces flow to **both** the Genkit DevUI and an external
    collector (Jaeger, Grafana Tempo, etc.) simultaneously.

    If no provider exists yet (running without the DevUI), one is
    created with the ``SERVICE_NAME`` resource attribute.

    Args:
        app: The ASGI application to instrument.
        endpoint: OTLP collector endpoint (e.g. ``http://localhost:4318``).
        protocol: Export protocol — ``'grpc'`` or ``'http/protobuf'``.
        service_name: Service name that appears in traces.
    """
    # Ensure a TracerProvider with SERVICE_NAME exists before adding
    # the exporter. If Genkit already created one (DevUI), this is a
    # no-op; otherwise we create one with proper resource attributes.
    _ensure_resource(service_name)

    # Add the OTLP exporter to the existing provider — this coexists
    # with Genkit's DevUI exporter when running in dev mode.
    exporter = _create_exporter(endpoint, protocol)
    add_custom_exporter(exporter, "otlp_collector")

    # Detect framework and apply appropriate instrumentation.
    app_type = type(app).__name__

    if isinstance(app, fastapi.FastAPI):
        _instrument_fastapi(app)
    elif app_type in ("Litestar", "Quart"):
        _instrument_asgi(app)
    else:
        logger.warning("Unknown ASGI framework, skipping instrumentation", app_type=app_type)
        return

    logger.info(
        "OpenTelemetry tracing enabled",
        endpoint=endpoint,
        protocol=protocol,
        service_name=service_name,
        framework=app_type,
    )
