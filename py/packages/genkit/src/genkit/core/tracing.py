# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Collects telemetry."""

import json
import os
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


class TelemetryServerSpanExporter(SpanExporter):
    """Implementation of :class:`SpanExporter` that prints spans to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    spans to the console STDOUT.
    """

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            span_data = {'traceId': f'{span.context.trace_id}', 'spans': {}}
            span_data['spans'][span.context.span_id] = {  # type: ignore
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
        return True


def convert_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for key in attributes:
        attrs[key] = attributes[key]
    return attrs


if 'GENKIT_ENV' in os.environ and os.environ['GENKIT_ENV'] == 'dev':
    provider = TracerProvider()
    processor = SimpleSpanProcessor(TelemetryServerSpanExporter())
    provider.add_span_processor(processor)
    # Sets the global default tracer provider
    trace_api.set_tracer_provider(provider)
    tracer = trace_api.get_tracer('genkit-tracer', 'v1', provider)
else:
    tracer = trace_api.get_tracer('genkit-tracer', 'v1')
