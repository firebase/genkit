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

"""Tests for the default telemetry exporter module.

This module tests:
    - TelemetryServerSpanExporter: Exports spans to a telemetry server
    - extract_span_data: Extracts span data for export
    - is_realtime_telemetry_enabled: Checks if realtime telemetry is enabled
    - create_span_processor: Creates appropriate span processor based on environment
    - init_telemetry_server_exporter: Initializes the telemetry server exporter
"""

import os
from unittest import mock
from unittest.mock import MagicMock, patch

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExportResult

from genkit.core.environment import EnvVar, GenkitEnvironment
from genkit.core.trace.default_exporter import (
    TelemetryServerSpanExporter,
    create_span_processor,
    extract_span_data,
    init_telemetry_server_exporter,
    is_realtime_telemetry_enabled,
)
from genkit.core.trace.realtime_processor import RealtimeSpanProcessor

# =============================================================================
# Tests for is_realtime_telemetry_enabled
# =============================================================================


def test_is_realtime_telemetry_enabled_when_not_set() -> None:
    """Test that realtime telemetry is disabled when env var is not set."""
    with mock.patch.dict(os.environ, clear=True):
        assert is_realtime_telemetry_enabled() is False


def test_is_realtime_telemetry_enabled_when_true() -> None:
    """Test that realtime telemetry is enabled when env var is 'true'."""
    with mock.patch.dict(os.environ, {'GENKIT_ENABLE_REALTIME_TELEMETRY': 'true'}):
        assert is_realtime_telemetry_enabled() is True


def test_is_realtime_telemetry_enabled_when_true_uppercase() -> None:
    """Test that realtime telemetry is enabled regardless of case."""
    with mock.patch.dict(os.environ, {'GENKIT_ENABLE_REALTIME_TELEMETRY': 'TRUE'}):
        assert is_realtime_telemetry_enabled() is True


def test_is_realtime_telemetry_enabled_when_true_mixed_case() -> None:
    """Test that realtime telemetry is enabled with mixed case."""
    with mock.patch.dict(os.environ, {'GENKIT_ENABLE_REALTIME_TELEMETRY': 'True'}):
        assert is_realtime_telemetry_enabled() is True


def test_is_realtime_telemetry_enabled_when_false() -> None:
    """Test that realtime telemetry is disabled when env var is 'false'."""
    with mock.patch.dict(os.environ, {'GENKIT_ENABLE_REALTIME_TELEMETRY': 'false'}):
        assert is_realtime_telemetry_enabled() is False


def test_is_realtime_telemetry_enabled_when_invalid() -> None:
    """Test that realtime telemetry is disabled with invalid value."""
    with mock.patch.dict(os.environ, {'GENKIT_ENABLE_REALTIME_TELEMETRY': 'invalid'}):
        assert is_realtime_telemetry_enabled() is False


def test_is_realtime_telemetry_enabled_when_empty() -> None:
    """Test that realtime telemetry is disabled when env var is empty."""
    with mock.patch.dict(os.environ, {'GENKIT_ENABLE_REALTIME_TELEMETRY': ''}):
        assert is_realtime_telemetry_enabled() is False


# =============================================================================
# Tests for create_span_processor
# =============================================================================


def test_create_span_processor_returns_realtime_in_dev_with_env_var() -> None:
    """Test that RealtimeSpanProcessor is returned in dev mode with env var set."""
    mock_exporter = MagicMock()

    with mock.patch.dict(
        os.environ,
        {
            EnvVar.GENKIT_ENV: GenkitEnvironment.DEV,
            'GENKIT_ENABLE_REALTIME_TELEMETRY': 'true',
        },
    ):
        processor = create_span_processor(mock_exporter)
        assert isinstance(processor, RealtimeSpanProcessor)


def test_create_span_processor_returns_simple_in_dev_without_env_var() -> None:
    """Test that SimpleSpanProcessor is returned in dev mode without env var."""
    mock_exporter = MagicMock()

    with mock.patch.dict(
        os.environ,
        {
            EnvVar.GENKIT_ENV: GenkitEnvironment.DEV,
        },
        clear=True,
    ):
        processor = create_span_processor(mock_exporter)
        assert isinstance(processor, SimpleSpanProcessor)


def test_create_span_processor_returns_batch_in_prod() -> None:
    """Test that BatchSpanProcessor is returned in production mode."""
    mock_exporter = MagicMock()

    with mock.patch.dict(
        os.environ,
        {
            EnvVar.GENKIT_ENV: GenkitEnvironment.PROD,
        },
    ):
        processor = create_span_processor(mock_exporter)
        assert isinstance(processor, BatchSpanProcessor)


def test_create_span_processor_returns_batch_when_no_env_set() -> None:
    """Test that BatchSpanProcessor is returned when no env is set (defaults to prod)."""
    mock_exporter = MagicMock()

    with mock.patch.dict(os.environ, clear=True):
        processor = create_span_processor(mock_exporter)
        assert isinstance(processor, BatchSpanProcessor)


def test_create_span_processor_ignores_realtime_env_in_prod() -> None:
    """Test that realtime env var is ignored in production mode (matches JS behavior)."""
    mock_exporter = MagicMock()

    with mock.patch.dict(
        os.environ,
        {
            EnvVar.GENKIT_ENV: GenkitEnvironment.PROD,
            'GENKIT_ENABLE_REALTIME_TELEMETRY': 'true',
        },
    ):
        processor = create_span_processor(mock_exporter)
        # Should still return BatchSpanProcessor in prod, not RealtimeSpanProcessor
        assert isinstance(processor, BatchSpanProcessor)


# =============================================================================
# Tests for init_telemetry_server_exporter
# =============================================================================


def test_init_telemetry_server_exporter_returns_exporter_when_url_set() -> None:
    """Test that exporter is returned when GENKIT_TELEMETRY_SERVER is set."""
    with mock.patch.dict(os.environ, {'GENKIT_TELEMETRY_SERVER': 'http://localhost:4000'}):
        exporter = init_telemetry_server_exporter()
        assert exporter is not None
        assert isinstance(exporter, TelemetryServerSpanExporter)
        assert exporter.telemetry_server_url == 'http://localhost:4000'


def test_init_telemetry_server_exporter_returns_none_when_url_not_set() -> None:
    """Test that None is returned when GENKIT_TELEMETRY_SERVER is not set."""
    with mock.patch.dict(os.environ, clear=True):
        exporter = init_telemetry_server_exporter()
        assert exporter is None


# =============================================================================
# Tests for TelemetryServerSpanExporter
# =============================================================================


def test_telemetry_server_exporter_init_default_endpoint() -> None:
    """Test TelemetryServerSpanExporter initialization with default endpoint."""
    exporter = TelemetryServerSpanExporter(telemetry_server_url='http://localhost:4000')

    assert exporter.telemetry_server_url == 'http://localhost:4000'
    assert exporter.telemetry_server_endpoint == '/api/traces'


def test_telemetry_server_exporter_init_custom_endpoint() -> None:
    """Test TelemetryServerSpanExporter initialization with custom endpoint."""
    exporter = TelemetryServerSpanExporter(
        telemetry_server_url='http://localhost:4000',
        telemetry_server_endpoint='/custom/traces',
    )

    assert exporter.telemetry_server_url == 'http://localhost:4000'
    assert exporter.telemetry_server_endpoint == '/custom/traces'


def test_telemetry_server_exporter_force_flush_returns_true() -> None:
    """Test that force_flush always returns True (no buffering)."""
    exporter = TelemetryServerSpanExporter(telemetry_server_url='http://localhost:4000')

    result = exporter.force_flush()
    assert result is True


def test_telemetry_server_exporter_force_flush_ignores_timeout() -> None:
    """Test that force_flush ignores the timeout parameter."""
    exporter = TelemetryServerSpanExporter(telemetry_server_url='http://localhost:4000')

    result = exporter.force_flush(timeout_millis=1)
    assert result is True


@patch('genkit.core.trace.default_exporter.httpx.Client')
def test_telemetry_server_exporter_export_sends_http_post(mock_client_class: MagicMock) -> None:
    """Test that export sends HTTP POST requests for each span."""
    # Setup mock client
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

    exporter = TelemetryServerSpanExporter(telemetry_server_url='http://localhost:4000')

    # Create a mock span
    mock_span = create_mock_span()

    # Export
    result = exporter.export([mock_span])

    # Verify
    assert result == SpanExportResult.SUCCESS
    mock_client.post.assert_called_once()


@patch('genkit.core.trace.default_exporter.httpx.Client')
def test_telemetry_server_exporter_export_multiple_spans(mock_client_class: MagicMock) -> None:
    """Test that export sends HTTP POST for each span in the sequence."""
    # Setup mock client
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client_class.return_value.__exit__ = MagicMock(return_value=None)

    exporter = TelemetryServerSpanExporter(telemetry_server_url='http://localhost:4000')

    # Create multiple mock spans
    mock_spans = [create_mock_span() for _ in range(3)]

    # Export
    result = exporter.export(mock_spans)

    # Verify
    assert result == SpanExportResult.SUCCESS
    assert mock_client.post.call_count == 3


# =============================================================================
# Tests for extract_span_data
# =============================================================================


def test_extract_span_data_basic_fields() -> None:
    """Test that extract_span_data extracts basic span fields correctly."""
    mock_span = create_mock_span(
        trace_id=12345,
        span_id=67890,
        name='test-span',
        start_time=1000000000,  # 1000ms in nanoseconds
        end_time=2000000000,  # 2000ms in nanoseconds
    )

    data = extract_span_data(mock_span)

    trace_id_hex = format(12345, '032x')
    span_id_hex = format(67890, '016x')

    assert data['traceId'] == trace_id_hex
    assert 'spans' in data
    assert span_id_hex in data['spans']

    span_info = data['spans'][span_id_hex]
    assert span_info['spanId'] == span_id_hex
    assert span_info['traceId'] == trace_id_hex
    assert span_info['displayName'] == 'test-span'
    assert span_info['startTime'] == 1000.0  # Converted to milliseconds
    assert span_info['endTime'] == 2000.0  # Converted to milliseconds


def test_extract_span_data_with_attributes() -> None:
    """Test that extract_span_data includes span attributes."""
    mock_span = create_mock_span(attributes={'key1': 'value1', 'key2': 123})

    data = extract_span_data(mock_span)

    span_id_hex = format(67890, '016x')
    span_info = data['spans'][span_id_hex]
    assert span_info['attributes'] == {'key1': 'value1', 'key2': 123}


def test_extract_span_data_with_parent_span() -> None:
    """Test that extract_span_data includes parent span ID when present."""
    mock_parent = MagicMock()
    mock_parent.span_id = 11111

    mock_span = create_mock_span()
    mock_span.parent = mock_parent

    data = extract_span_data(mock_span)

    span_id_hex = format(67890, '016x')
    parent_span_id_hex = format(11111, '016x')
    span_info = data['spans'][span_id_hex]
    assert span_info['parentSpanId'] == parent_span_id_hex


def test_extract_span_data_without_parent_span() -> None:
    """Test that extract_span_data omits parent span ID when not present."""
    mock_span = create_mock_span()
    mock_span.parent = None

    data = extract_span_data(mock_span)

    span_id_hex = format(67890, '016x')
    span_info = data['spans'][span_id_hex]
    assert 'parentSpanId' not in span_info

    # Root span should have displayName, startTime, endTime at top level
    assert data['displayName'] == 'test-span'


def test_extract_span_data_includes_status() -> None:
    """Test that extract_span_data includes span status."""
    mock_span = create_mock_span()

    data = extract_span_data(mock_span)

    span_id_hex = format(67890, '016x')
    span_info = data['spans'][span_id_hex]
    assert 'status' in span_info
    assert span_info['status']['code'] == trace_api.StatusCode.OK.value  # OK status is 1


def test_extract_span_data_includes_instrumentation_library() -> None:
    """Test that extract_span_data includes instrumentation library info."""
    mock_span = create_mock_span()

    data = extract_span_data(mock_span)

    span_id_hex = format(67890, '016x')
    span_info = data['spans'][span_id_hex]
    assert span_info['instrumentationLibrary'] == {
        'name': 'genkit-tracer',
        'version': 'v1',
    }


def test_extract_span_data_handles_none_times() -> None:
    """Test that extract_span_data handles None start/end times."""
    mock_span = create_mock_span(start_time=None, end_time=None)

    data = extract_span_data(mock_span)

    span_id_hex = format(67890, '016x')
    span_info = data['spans'][span_id_hex]
    assert span_info['startTime'] == 0
    assert span_info['endTime'] == 0


# =============================================================================
# Helper functions
# =============================================================================


def create_mock_span(
    trace_id: int = 12345,
    span_id: int = 67890,
    name: str = 'test-span',
    start_time: int | None = 1000000000,
    end_time: int | None = 2000000000,
    attributes: dict | None = None,
) -> MagicMock:
    """Create a mock ReadableSpan for testing.

    Args:
        trace_id: The trace ID.
        span_id: The span ID.
        name: The span name.
        start_time: Start time in nanoseconds.
        end_time: End time in nanoseconds.
        attributes: Optional span attributes.

    Returns:
        A MagicMock configured as a ReadableSpan.
    """
    mock_span = MagicMock(spec=ReadableSpan)

    # Configure context
    mock_context = MagicMock()
    mock_context.trace_id = trace_id
    mock_context.span_id = span_id
    mock_span.context = mock_context

    # Configure basic properties
    mock_span.name = name
    mock_span.start_time = start_time
    mock_span.end_time = end_time
    mock_span.attributes = attributes or {}
    mock_span.parent = None

    # Configure kind
    mock_span.kind = trace_api.SpanKind.INTERNAL

    # Configure status
    mock_status = MagicMock()
    mock_status.status_code = trace_api.StatusCode.OK
    mock_status.description = None
    mock_span.status = mock_status

    return mock_span
