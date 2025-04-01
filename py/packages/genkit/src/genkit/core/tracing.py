# Copyright 2025 Google LLC
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


"""Telemetry and tracing functionality for the Genkit framework.

This module provides functionality for collecting and exporting telemetry data
from Genkit operations. It uses OpenTelemetry for tracing and exports span
data to a telemetry server for monitoring and debugging purposes.

The module includes:
    - A custom span exporter for sending trace data to a telemetry server
    - Utility functions for converting and formatting trace attributes
    - Configuration for development environment tracing
"""

import json
import sys
from collections.abc import Sequence
from typing import Any

import requests  # type: ignore[import-untyped]
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

from genkit.core.environment import is_dev_environment


def extract_span_data(span: ReadableSpan) -> dict[str, Any]:
    """Extract span data from a ReadableSpan object.

    This function extracts the span data from a ReadableSpan object and returns
    a dictionary containing the span data.
    """
    span_data = {'traceId': f'{span.context.trace_id}', 'spans': {}}
    span_data['spans'][span.context.span_id] = {
        'spanId': f'{span.context.span_id}',
        'traceId': f'{span.context.trace_id}',
        'startTime': span.start_time / 1000000,
        'endTime': span.end_time / 1000000,
        'attributes': convert_attributes(
            attributes=span.attributes,  # type: ignore
        ),
        'displayName': span.name,
        # "links": span.links,
        'spanKind': trace_api.SpanKind(span.kind).name,
        'parentSpanId': f'{span.parent.span_id}' if span.parent else None,
        'status': (
            {
                'code': trace_api.StatusCode(span.status.status_code).value,
                'description': span.status.description,
            }
            if span.status
            else None
        ),
        'instrumentationLibrary': {
            'name': 'genkit-tracer',
            'version': 'v1',
        },
        # "timeEvents": {
        #     timeEvent: span.events.map((e)=> ({
        #         time: transformTime(e.time),
        #         annotation: {
        #             attributes: e.attributes ?? {},
        #             description: e.name,
        #         },
        #     })),
        # },
    }
    if not span_data['spans'][span.context.span_id]['parentSpanId']:  # type: ignore
        del span_data['spans'][span.context.span_id]['parentSpanId']  # type: ignore

    if not span.parent:
        span_data['displayName'] = span.name
        span_data['startTime'] = span.start_time
        span_data['endTime'] = span.end_time

    return span_data


class TelemetryServerSpanExporter(SpanExporter):
    """Exports spans to a Genkit telemetry server.

    This exporter sends span data in a specific JSON format to a telemetry server,
    typically running locally during development, for visualization and debugging.

    Attributes:
        telemetry_server_url: The URL of the telemetry server endpoint.
    """

    def __init__(self, telemetry_server_url: str = 'http://localhost:4033/api/traces'):
        """Initializes the TelemetryServerSpanExporter.

        Args:
            telemetry_server_url: The URL of the telemetry server's trace endpoint.
                                  Defaults to 'http://localhost:4033/api/traces'.
        """
        self.telemetry_server_url = telemetry_server_url

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Exports a sequence of ReadableSpans to the configured telemetry server.

        Iterates through the provided spans, extracts relevant data using
        `extract_span_data`, converts it to JSON, and sends it via an HTTP POST
        request to the `telemetry_server_url`.

        Note:
            This currently uses the `requests` library synchronously. Future
            versions might switch to an asynchronous HTTP client like `aiohttp`.

        Args:
            spans: A sequence of OpenTelemetry ReadableSpan objects to export.

        Returns:
            SpanExportResult.SUCCESS upon successful processing (does not guarantee
            server-side success).
        """
        for span in spans:
            # TODO: telemetry server URL must be dynamic, whatever tools
            # notification says.
            # TODO: replace this with aiohttp client.
            requests.post(
                self.telemetry_server_url,
                data=json.dumps(extract_span_data(span)),
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            )

        sys.stdout.flush()
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Forces the exporter to flush any buffered spans.

        Since this exporter sends spans immediately in the `export` method,
        this method currently does nothing but return True.

        Args:
            timeout_millis: The maximum time in milliseconds to wait for the flush.
                            This parameter is ignored in the current implementation.

        Returns:
            True, indicating the flush operation is considered complete.
        """
        return True


def convert_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Convert span attributes to a format suitable for export.

    This function creates a new dictionary containing the span attributes,
    ensuring they are in a format that can be properly serialized.

    Args:
        attributes: Dictionary of span attributes to convert.

    Returns:
        A new dictionary containing the converted attributes.
    """
    attrs: dict[str, Any] = {}
    for key in attributes:
        attrs[key] = attributes[key]
    return attrs


if is_dev_environment():
    provider = TracerProvider()
    processor = SimpleSpanProcessor(
        TelemetryServerSpanExporter(
            telemetry_server_url='http://localhost:4033/api/traces',
        )
    )
    provider.add_span_processor(processor)
    # Sets the global default tracer provider
    trace_api.set_tracer_provider(provider)
    tracer = trace_api.get_tracer('genkit-tracer', 'v1', provider)
else:
    tracer = trace_api.get_tracer('genkit-tracer', 'v1')
