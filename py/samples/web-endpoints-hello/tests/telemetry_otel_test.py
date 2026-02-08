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

Validates _ensure_resource, _create_exporter, _instrument_fastapi,
_instrument_asgi, and setup_otel_instrumentation with mocked exporters.

Run with::

    cd py/samples/web-endpoints-hello
    uv run pytest tests/telemetry_otel_test.py -v
"""

import sys
from unittest.mock import MagicMock, patch

import fastapi
from opentelemetry.sdk.trace import TracerProvider

from src.telemetry import (
    _create_exporter,  # noqa: PLC2701 - testing private function
    _ensure_resource,  # noqa: PLC2701 - testing private function
    _instrument_asgi,  # noqa: PLC2701 - testing private function
    _instrument_fastapi,  # noqa: PLC2701 - testing private function
    setup_otel_instrumentation,
)


def test_ensure_resource_creates_provider_when_none_exists() -> None:
    """_ensure_resource creates a TracerProvider with SERVICE_NAME."""
    with (
        patch("src.telemetry.trace.get_tracer_provider", return_value=None),
        patch("src.telemetry.trace.set_tracer_provider") as mock_set,
        patch("src.telemetry.TracerProvider") as mock_tp_cls,
        patch("src.telemetry.Resource") as mock_resource_cls,
    ):
        _ensure_resource("my-service")

    mock_resource_cls.assert_called_once()
    mock_tp_cls.assert_called_once()
    mock_set.assert_called_once()


def test_ensure_resource_noop_when_provider_exists() -> None:
    """_ensure_resource is a no-op when a TracerProvider already exists."""
    mock_existing = MagicMock(spec=TracerProvider)
    mock_existing.__class__ = TracerProvider  # pyright: ignore[reportAttributeAccessIssue] - mock pattern for isinstance

    with (
        patch("src.telemetry.trace.get_tracer_provider", return_value=mock_existing),
        patch("src.telemetry.trace.set_tracer_provider") as mock_set,
    ):
        _ensure_resource("my-service")

    mock_set.assert_not_called()


def test_create_exporter_http() -> None:
    """_create_exporter creates an HTTP exporter by default."""
    with patch("src.telemetry.HTTPSpanExporter") as mock_http_cls:
        exporter = _create_exporter("http://localhost:4318", "http/protobuf")

    mock_http_cls.assert_called_once_with(endpoint="http://localhost:4318/v1/traces")
    assert exporter == mock_http_cls.return_value


def test_create_exporter_grpc() -> None:
    """_create_exporter uses gRPC exporter when protocol is 'grpc'."""
    mock_grpc_cls = MagicMock()
    mock_grpc_module = MagicMock()
    mock_grpc_module.OTLPSpanExporter = mock_grpc_cls

    with (
        patch("src.telemetry.HTTPSpanExporter"),
        patch.dict(
            "sys.modules",
            {
                "opentelemetry.exporter.otlp.proto.grpc": MagicMock(),
                "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": mock_grpc_module,
            },
        ),
    ):
        exporter = _create_exporter("http://localhost:4317", "grpc")

    mock_grpc_cls.assert_called_once_with(endpoint="http://localhost:4317")
    assert exporter == mock_grpc_cls.return_value


def test_create_exporter_grpc_fallback_on_import_error() -> None:
    """_create_exporter falls back to HTTP if gRPC exporter is missing."""
    saved = {}
    for key in list(sys.modules):
        if "grpc" in key and "opentelemetry" in key:
            saved[key] = sys.modules.pop(key)

    try:
        with (
            patch("src.telemetry.HTTPSpanExporter") as mock_http,
            patch.dict(
                "sys.modules",
                {
                    "opentelemetry.exporter.otlp.proto.grpc": None,
                    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
                },
            ),
        ):
            _create_exporter("http://localhost:4317", "grpc")

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
    mock_app.__class__ = fastapi.FastAPI  # pyright: ignore[reportAttributeAccessIssue] - mock pattern for isinstance

    with (
        patch("src.telemetry._ensure_resource"),
        patch("src.telemetry._create_exporter") as mock_create,
        patch("src.telemetry.add_custom_exporter") as mock_add,
        patch("src.telemetry._instrument_fastapi") as mock_inst,
    ):
        setup_otel_instrumentation(mock_app, "http://localhost:4318", "http/protobuf", "svc")

    mock_create.assert_called_once_with("http://localhost:4318", "http/protobuf")
    mock_add.assert_called_once_with(mock_create.return_value, "otlp_collector")
    mock_inst.assert_called_once_with(mock_app)


def test_setup_otel_litestar() -> None:
    """setup_otel_instrumentation instruments a Litestar-like app."""

    class FakeLitestar:
        """Fake Litestar class with correct __name__."""

        pass

    FakeLitestar.__name__ = "Litestar"
    mock_app = FakeLitestar()

    with (
        patch("src.telemetry._ensure_resource"),
        patch("src.telemetry._create_exporter"),
        patch("src.telemetry.add_custom_exporter"),
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
        patch("src.telemetry._ensure_resource"),
        patch("src.telemetry._create_exporter"),
        patch("src.telemetry.add_custom_exporter"),
        patch("src.telemetry._instrument_fastapi") as mock_fa,
        patch("src.telemetry._instrument_asgi") as mock_asgi,
    ):
        setup_otel_instrumentation(Unknown(), "http://localhost:4318", "http/protobuf", "svc")

    mock_fa.assert_not_called()
    mock_asgi.assert_not_called()
