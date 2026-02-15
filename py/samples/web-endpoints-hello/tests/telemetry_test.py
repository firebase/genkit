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

"""Telemetry integration tests using OpenTelemetry's InMemorySpanExporter.

Verifies that FastAPI instrumentation produces proper trace spans
for each endpoint without requiring an external collector like Jaeger.

The TracerProvider is set up in conftest.py (because OTel only allows
setting it once per process). Tests here instrument the app, make
requests, and assert on the captured spans.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from conftest import otel_exporter
from endpoints_test import app, mock_ai
from httpx import ASGITransport, AsyncClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME

# Instrument FastAPI — idempotent guard prevents double-instrumentation
# when both endpoints_test.py and this file run in the same session.
if not FastAPIInstrumentor().is_instrumented_by_opentelemetry:  # pyrefly: ignore[missing-attribute] — not in type stubs
    FastAPIInstrumentor.instrument_app(app)


@pytest.fixture(autouse=True)
def _clear_spans() -> None:
    """Clear captured spans before each test."""
    otel_exporter.clear()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_creates_trace_span(client: AsyncClient) -> None:
    """GET /health should produce a trace span with the correct HTTP attributes."""
    response = await client.get("/health")
    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")

    spans = otel_exporter.get_finished_spans()
    if not spans:
        pytest.fail("Expected at least one span, got none")

    health_spans = [s for s in spans if s.attributes and s.attributes.get("http.route") == "/health"]
    if not health_spans:
        all_routes = [s.attributes.get("http.route", "N/A") for s in spans if s.attributes]
        pytest.fail(f"No span with http.route=/health. Routes found: {all_routes}")

    span = health_spans[0]
    if span.attributes is None:
        pytest.fail("Span has no attributes")
    attrs = dict(span.attributes)
    method = attrs.get("http.method", attrs.get("http.request.method"))
    if method != "GET":
        pytest.fail(f"Expected GET method, got {method}")


@pytest.mark.asyncio
async def test_tell_joke_creates_trace_span(client: AsyncClient) -> None:
    """POST /tell-joke should produce a trace span."""
    mock_result = MagicMock()
    mock_result.text = "Why did the cat sit on the computer?"
    mock_ai.generate = AsyncMock(return_value=mock_result)

    response = await client.post("/tell-joke", json={"name": "Mittens"})

    if response.status_code != 200:
        pytest.fail(f"Expected 200, got {response.status_code}")

    spans = otel_exporter.get_finished_spans()
    joke_spans = [s for s in spans if s.attributes and s.attributes.get("http.route") == "/tell-joke"]
    if not joke_spans:
        all_routes = [s.attributes.get("http.route", "N/A") for s in spans if s.attributes]
        pytest.fail(f"No span for /tell-joke. Routes found: {all_routes}")


@pytest.mark.asyncio
async def test_trace_has_correct_service_name(client: AsyncClient) -> None:
    """Spans should carry the configured service name resource."""
    await client.get("/health")

    spans = otel_exporter.get_finished_spans()
    if not spans:
        pytest.fail("No spans captured")

    resource = spans[0].resource
    service_name = resource.attributes.get(SERVICE_NAME)
    if service_name != "test-service":
        pytest.fail(f'Expected service name "test-service", got {service_name!r}')


@pytest.mark.asyncio
async def test_multiple_requests_create_independent_spans(client: AsyncClient) -> None:
    """Each request should produce its own trace span with a unique trace ID."""
    await client.get("/health")
    await client.get("/health")

    spans = otel_exporter.get_finished_spans()
    health_spans = [s for s in spans if s.attributes and s.attributes.get("http.route") == "/health"]
    if len(health_spans) < 2:
        pytest.fail(f"Expected at least 2 spans for /health, got {len(health_spans)}")

    trace_ids = {s.context.trace_id for s in health_spans if s.context}
    if len(trace_ids) < 2:
        pytest.fail(f"Expected unique trace IDs per request, got {len(trace_ids)}")


@pytest.mark.asyncio
async def test_error_request_captures_span(client: AsyncClient) -> None:
    """A 404 request should still create a span."""
    response = await client.get("/nonexistent-endpoint-for-testing")

    if response.status_code != 404:
        pytest.fail(f"Expected 404, got {response.status_code}")

    spans = otel_exporter.get_finished_spans()
    if not spans:
        pytest.fail("Expected at least one span even for 404 requests")
