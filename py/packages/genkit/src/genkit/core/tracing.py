# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


import json
import os
import requests
import sys

from typing import Any, Dict, Sequence
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SpanExporter,
    SpanExportResult,
    SimpleSpanProcessor,
)
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan


class TelemetryServerSpanExporter(SpanExporter):
    """Implementation of :class:`SpanExporter` that prints spans to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    spans to the console STDOUT.
    """

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            spanData = {'traceId': f'{span.context.trace_id}', 'spans': {}}
            spanData['spans'][span.context.span_id] = {
                'spanId': f'{span.context.span_id}',
                'traceId': f'{span.context.trace_id}',
                'startTime': span.start_time / 1000000,
                'endTime': span.end_time / 1000000,
                'attributes': convert_attributes(span.attributes),
                'displayName': span.name,
                # "links": span.links,
                'spanKind': trace_api.SpanKind(span.kind).name,
                'parentSpanId': f'{span.parent.span_id}'
                if span.parent is not None
                else None,
                'status': {
                    'code': trace_api.StatusCode(span.status.status_code).value,
                    'description': span.status.description,
                }
                if span.status is not None
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
            if spanData['spans'][span.context.span_id]['parentSpanId'] is None:
                del spanData['spans'][span.context.span_id]['parentSpanId']

            if span.parent is None:
                spanData['displayName'] = span.name
                spanData['startTime'] = span.start_time
                spanData['endTime'] = span.end_time

            # TODO: telemetry server URL must be dynamic, whatever tools notification says
            requests.post(
                'http://localhost:4033/api/traces',
                data=json.dumps(spanData),
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            )

        sys.stdout.flush()
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def convert_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {}
    for key in attributes:
        attrs[key] = attributes[key]
    return attrs


if 'GENKIT_ENV' in os.environ and os.environ['GENKIT_ENV'] == 'dev':
    provider = TracerProvider()
    processor = SimpleSpanProcessor(TelemetryServerSpanExporter())
    provider.add_span_processor(processor)
    # Sets the global default tracer provider
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer('genkit-tracer', 'v1', provider)
else:
    tracer = trace.get_tracer('genkit-tracer', 'v1')
