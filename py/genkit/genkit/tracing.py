# Copyright 2022 Google Inc.
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

from pydantic import BaseModel, TypeAdapter
import inspect
from typing import Union, List, Dict, Optional, Callable, Any, Sequence, IO
import json
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SpanExportResult,
    SimpleSpanProcessor,
)
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.util._once import Once
import requests
import sys

class ConsoleSpanExporter(SpanExporter):
    """Implementation of :class:`SpanExporter` that prints spans to the
    console.

    This class can be used for diagnostic purposes. It prints the exported
    spans to the console STDOUT.
    """

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            spanData = {
                "traceId": f"{span.context.trace_id}",
                "spans": {}
            }
            spanData["spans"][span.context.span_id] = {
                "spanId": f"{span.context.span_id}",
                "traceId": f"{span.context.trace_id}",
                "startTime": span.start_time / 1000000,
                "endTime": span.end_time / 1000000,
                "attributes": convert_attributes(span.attributes),
                "displayName": span.name,
                # "links": span.links,
                "spanKind": trace_api.SpanKind(span.kind).name,
                "parentSpanId": f"{span.parent.span_id}" if span.parent != None else None,
                "status": {"code": trace_api.StatusCode(span.status.status_code).value, "description": span.status.description} if span.status != None else None,
                "instrumentationLibrary": {
                    "name": "genkit-tracer",
                    "version": "v1"
                }

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
            if spanData["spans"][span.context.span_id]["parentSpanId"] == None:
                del spanData["spans"][span.context.span_id]['parentSpanId']

            if span.parent == None:
                spanData["displayName"] = span.name
                spanData["startTime"] = span.start_time
                spanData["endTime"] = span.end_time

            #print(json.dumps(spanData, indent=2))
            requests.post(f"http://localhost:4033/api/traces", data=json.dumps(spanData), headers={
                          'Content-Type': 'application/json', 'Accept': 'application/json'})

        sys.stdout.flush()
        return SpanExportResult.SUCCESS

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def convert_attributes(attributes):
    attrs = {}
    for key in attributes:
        attrs[key] = attributes[key]
    return attrs


provider = TracerProvider()
# processor = SimpleSpanProcessor(TelemetryServerSpanExporter('http://localhost:4033'))
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
# Sets the global default tracer provider
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("genkit-tracer", "v1", provider)
