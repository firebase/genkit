# Copyright 2025 Google LLC
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
from genkit.core.environment import is_dev_environment
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)


class TelemetryServerSpanExporter(SpanExporter):
    """SpanExporter implementation that exports spans to a telemetry server.

    This exporter sends span data to a telemetry server (default:
    http://localhost:4033) for monitoring and debugging.  Each span is converted
    to a JSON format that includes trace ID, span ID, timing information,
    attributes, and other metadata about the operation.
    """

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export the spans to the telemetry server.

        This method processes each span in the sequence, converts it to the
        required JSON format, and sends it to the telemetry server via HTTP
        POST.

        Args:
            spans: A sequence of ReadableSpan objects to export.

        Returns:
            SpanExportResult.SUCCESS if the export was successful.
        """
        for span in spans:
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
                'parentSpanId': f'{span.parent.span_id}'
                if span.parent
                else None,
                'status': {
                    'code': trace_api.StatusCode(span.status.status_code).value,
                    'description': span.status.description,
                }
                if span.status
                else None,
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

            # TODO: telemetry server URL must be dynamic,
            # whatever tools notification says
            requests.post(
                'http://localhost:4033/api/traces',
                data=json.dumps(span_data),
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            )

        sys.stdout.flush()
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any pending spans to the telemetry server.

        Args:
            timeout_millis: Maximum time to wait for the flush to complete.

        Returns:
            True if the flush was successful, False otherwise.
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
    processor = SimpleSpanProcessor(TelemetryServerSpanExporter())
    provider.add_span_processor(processor)
    # Sets the global default tracer provider
    trace_api.set_tracer_provider(provider)
    tracer = trace_api.get_tracer('genkit-tracer', 'v1', provider)
else:
    tracer = trace_api.get_tracer('genkit-tracer', 'v1')
