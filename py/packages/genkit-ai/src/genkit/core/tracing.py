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
import traceback
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from typing import Any, TypeVar

import requests  # type: ignore[import-untyped]
import structlog
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.util import types
from pydantic import BaseModel

from genkit.core.environment import is_dev_environment
from genkit.core.typing import SpanMetadata

ATTR_PREFIX = 'genkit'
logger = structlog.getLogger(__name__)


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
                'status': (
                    {
                        'code': trace_api.StatusCode(
                            span.status.status_code
                        ).value,
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

T = TypeVar('T')


@contextmanager
def run_in_new_span[T](
    metadata: SpanMetadata,
    labels: dict[str, str] | None = None,
    links: list[trace_api.Link] | None = None,
):
    """Starts a new span context under the current trace.

    This method provides a contexmanager for working with Genkit spans. The
    context object is a `GenkitSpan`, which is a light wrapper on OpenTelemetry
    span object, with handling for genkit attributes.
    """
    with tracer.start_as_current_span(
        name=metadata.name, links=links
    ) as ot_span:
        try:
            span = GenkitSpan(ot_span, labels)
            yield span
            span.set_genkit_attribute('status', 'success')
        except Exception as e:
            logger.debug(f'Error in run_in_new_span: {str(e)}')
            logger.debug(traceback.format_exc())
            span.set_genkit_attribute('status', 'error')
            span.set_status(
                status=trace_api.StatusCode.ERROR, description=str(e)
            )
            span.record_exception(e)
            raise e


class GenkitSpan:
    """Light wrapper for Span, specific to Genkit."""

    is_root: bool
    _span: trace_api.Span

    def __init__(
        self, span: trace_api.Span, labels: dict[str, str] | None = None
    ):
        """Create GenkitSpan."""
        self._span = span
        parent = span.parent
        self.is_root = False
        if parent is None:
            self.is_root = True
        if labels is not None:
            self.set_attributes(labels)

    def __getattr__(self, name):
        """Passthrough for all OpenTelemetry Span attributes."""
        return getattr(self._span, name)

    def get_otel_span(self):
        """Return underlying OpenTelemetry span."""
        return self._span

    def set_genkit_attribute(self, key: str, value: types.AttributeValue):
        """Set Genkit specific attribute, with the `genkit` prefix."""
        if key == 'metadata' and isinstance(value, dict) and value:
            for meta_key, meta_value in value.items():
                self._span.set_attribute(
                    f'{ATTR_PREFIX}:metadata:{meta_key}', str(meta_value)
                )
        elif isinstance(value, dict):
            self._span.set_attribute(f'{ATTR_PREFIX}:{key}', json.dumps(value))
        else:
            self._span.set_attribute(f'{ATTR_PREFIX}:{key}', str(value))

    def set_genkit_attributes(
        self, attributes: Mapping[str, types.AttributeValue]
    ):
        """Set Genkit specific attributes, with the `genkit` prefix."""
        for key, value in attributes.items():
            self.set_genkit_attribute(key, value)

    def span_id(self):
        """Returns the span_id."""
        return str(self._span.get_span_context().span_id)

    def trace_id(self):
        """Returns the trace_id."""
        return str(self._span.get_span_context().trace_id)

    def set_input(self, input: Any):
        """Set Genkit Span input, visible in the trace viewer."""
        value = None
        if isinstance(input, BaseModel):
            value = input.model_dump_json(by_alias=True, exclude_none=True)
        else:
            value = json.dumps(input)
        self.set_genkit_attribute('input', value)

    def set_output(self, output: Any):
        """Set Genkit Span output, visible in the trace viewer."""
        value = None
        if isinstance(output, BaseModel):
            value = output.model_dump_json(by_alias=True, exclude_none=True)
        else:
            value = json.dumps(output)
        self.set_genkit_attribute('output', value)
