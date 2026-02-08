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

"""Tests for OpenTelemetry instrumentation setup.

Validates _create_provider, _instrument_fastapi, _instrument_asgi,
and setup_otel_instrumentation with mocked OTLP exporters.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/telemetry_otel_test.py -v
"""

import sys
from unittest.mock import MagicMock, patch

import fastapi

from src.telemetry import (
    _create_provider,  # noqa: PLC2701 - testing private function
    _instrument_asgi,  # noqa: PLC2701 - testing private function
    _instrument_fastapi,  # noqa: PLC2701 - testing private function
    setup_otel_instrumentation,
)


def test_create_provider_http() -> None:
    """_create_provider creates a TracerProvider with HTTP exporter."""
    with (
        patch("src.telemetry.HTTPSpanExporter") as mock_exporter_cls,
        patch("src.telemetry.BatchSpanProcessor") as mock_processor_cls,
        patch("src.telemetry.trace.set_tracer_provider") as mock_set,
    ):
        provider = _create_provider("http://localhost:4318", "http/protobuf", "test-service")

    mock_exporter_cls.assert_called_once_with(endpoint="http://localhost:4318/v1/traces")
    mock_processor_cls.assert_called_once()
    mock_set.assert_called_once_with(provider)


def test_create_provider_grpc() -> None:
    """_create_provider uses gRPC exporter when protocol is 'grpc'."""
    mock_grpc_cls = MagicMock()
    mock_grpc_module = MagicMock()
    mock_grpc_module.OTLPSpanExporter = mock_grpc_cls

    with (
        patch("src.telemetry.HTTPSpanExporter"),
        patch("src.telemetry.BatchSpanProcessor"),
        patch("src.telemetry.trace.set_tracer_provider"),
        patch.dict(
            "sys.modules",
            {
                "opentelemetry.exporter.otlp.proto.grpc": MagicMock(),
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": mock_grpc_module,
            },
        ),
    ):
        _create_provider("http://localhost:4317", "grpc", "test-service")

    mock_grpc_cls.assert_called_once_with(endpoint="http://localhost:4317")


def test_create_provider_grpc_fallback_on_import_error() -> None:
    """_create_provider falls back to HTTP if gRPC exporter is missing."""
    # Remove the gRPC module from sys.modules so the import inside
    # _create_provider triggers a fresh import attempt.
    saved = {}
    for key in list(sys.modules):
        if "grpc" in key and "opentelemetry" in key:
            saved[key] = sys.modules.pop(key)

    try:
        with (
            patch("src.telemetry.HTTPSpanExporter") as mock_http,
            patch("src.telemetry.BatchSpanProcessor"),
            patch("src.telemetry.trace.set_tracer_provider"),
            patch.dict(
                "sys.modules",
                {
                    "opentelemetry.exporter.otlp.proto.grpc": None,
                    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
                },
            ),
        ):
            # Should not raise — falls back to HTTP.
            _create_provider("http://localhost:4317", "grpc", "test-service")

        mock_http.assert_called_once()
    finally:
        sys.modules.update(saved)


def test_instrument_fastapi() -> None:
    """_instrument_fastapi calls FastAPIInstrumentor.instrument_app."""
    mock_app = MagicMock(spec=fastapi.FastAPI)
    with patch("src.telemetry.FastAPIInstrumentor") as mock_instrumentor:
        _instrument_fastapi(mock_app)

    mock_instrumentor.instrument_app.assert_called_once_with(mock_app)


def test_instrument_asgi_with_handler() -> None:
    """_instrument_asgi wraps the asgi_handler with OTel middleware."""
    original_handler = MagicMock(name="original_handler")
    mock_app = MagicMock()
    mock_app.asgi_handler = original_handler

    with patch("src.telemetry.OpenTelemetryMiddleware") as mock_otel_mw:
        _instrument_asgi(mock_app)

    mock_otel_mw.assert_called_once_with(original_handler)


def test_instrument_asgi_without_handler() -> None:
    """_instrument_asgi skips instrumentation when no asgi_handler."""
    mock_app = MagicMock(spec=[])  # No attributes at all.
    _instrument_asgi(mock_app)  # Should not raise.


def test_setup_otel_fastapi() -> None:
    """setup_otel_instrumentation instruments a FastAPI app."""
    mock_app = MagicMock(spec=fastapi.FastAPI)
    # Make isinstance check work.
    mock_app.__class__ = fastapi.FastAPI  # pyright: ignore[reportAttributeAccessIssue] - mock pattern for isinstance

    with (
        patch("src.telemetry._create_provider"),
        patch("src.telemetry._instrument_fastapi") as mock_inst,
    ):
        setup_otel_instrumentation(mock_app, "http://localhost:4318", "http/protobuf", "svc")

    mock_inst.assert_called_once_with(mock_app)


def test_setup_otel_litestar() -> None:
    """setup_otel_instrumentation instruments a Litestar-like app."""

    class FakeLitestar:
        """Fake Litestar class with correct __name__."""

        pass

    FakeLitestar.__name__ = "Litestar"
    mock_app = FakeLitestar()

    with (
        patch("src.telemetry._create_provider"),
        patch("src.telemetry._instrument_asgi") as mock_inst,
    ):
        setup_otel_instrumentation(mock_app, "http://localhost:4318", "http/protobuf", "svc")

    mock_inst.assert_called_once_with(mock_app)


def test_setup_otel_unknown_framework() -> None:
    """setup_otel_instrumentation logs warning for unknown frameworks."""

    class Unknown:
        """Unknown framework type."""

        pass

    with (
        patch("src.telemetry._create_provider"),
        patch("src.telemetry._instrument_fastapi") as mock_fa,
        patch("src.telemetry._instrument_asgi") as mock_asgi,
    ):
        setup_otel_instrumentation(Unknown(), "http://localhost:4318", "http/protobuf", "svc")

    mock_fa.assert_not_called()
    mock_asgi.assert_not_called()
