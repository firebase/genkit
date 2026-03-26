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

"""Telemetry and tracing default exporter for the Genkit framework."""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, cast
from urllib.parse import urljoin

import httpx
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.trace import SpanContext

from genkit._core._compat import override
from genkit._core._environment import is_dev_environment
from genkit._core._logger import get_logger

from ._realtime_processor import RealtimeSpanProcessor

logger = get_logger(__name__)

INSTRUMENTATION = {'name': 'genkit-tracer', 'version': 'v1'}
TRACE_HEADERS = {'Content-Type': 'application/json', 'Accept': 'application/json'}


def _ns_to_ms(ns: int | None) -> float:
    return ns / 1_000_000 if ns is not None else 0


def extract_span_data(span: ReadableSpan) -> dict[str, Any]:
    """Convert ReadableSpan to Genkit telemetry server JSON format."""
    ctx = cast(SpanContext, span.context)
    trace_id = format(ctx.trace_id, '032x')
    span_id = format(ctx.span_id, '016x')
    parent_id = format(span.parent.span_id, '016x') if span.parent else None
    start = _ns_to_ms(span.start_time)
    end = _ns_to_ms(span.end_time)

    span_entry: dict[str, Any] = {
        'spanId': span_id,
        'traceId': trace_id,
        'startTime': start,
        'endTime': end,
        'attributes': dict(span.attributes or {}),
        'displayName': span.name,
        'spanKind': trace_api.SpanKind(span.kind).name,
        'instrumentationLibrary': {'name': 'genkit-tracer', 'version': 'v1'},
    }
    if parent_id:
        span_entry['parentSpanId'] = parent_id
    if span.status:
        span_entry['status'] = {
            'code': trace_api.StatusCode(span.status.status_code).value,
            'description': span.status.description,
        }

    result: dict[str, Any] = {'traceId': trace_id, 'spans': {span_id: span_entry}}
    if not span.parent:
        result['displayName'] = span.name
        result['startTime'] = start
        result['endTime'] = end

    return result


DEFAULT_SPAN_FILTERS: dict[str, str] = {
    # Suppress prompt runner preview traces (triggered on every keystroke in Dev UI)
    'genkit:metadata:subtype': 'prompt',
}


class TraceServerExporter(SpanExporter):
    """Exports spans to Genkit telemetry server (DevUI)."""

    def __init__(
        self,
        telemetry_server_url: str,
        telemetry_server_endpoint: str = '/api/traces',
        filters: dict[str, str] | None = None,
    ) -> None:
        self.telemetry_server_url = telemetry_server_url
        self.telemetry_server_endpoint = telemetry_server_endpoint
        self.filters = filters if filters is not None else DEFAULT_SPAN_FILTERS

    @override
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        # Collect trace IDs that should be filtered out entirely
        filtered_trace_ids: set[str] = set()
        for span in spans:
            attrs = span.attributes or {}
            if any(attrs.get(k) == v for k, v in self.filters.items()):
                if span.context:
                    filtered_trace_ids.add(format(span.context.trace_id, '032x'))

        url = urljoin(self.telemetry_server_url, self.telemetry_server_endpoint)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        with httpx.Client() as client:
            for span in spans:
                if span.context and format(span.context.trace_id, '032x') in filtered_trace_ids:
                    continue
                client.post(url, json=extract_span_data(span), headers=headers)
        return SpanExportResult.SUCCESS

    @override
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def init_telemetry_server_exporter() -> SpanExporter | None:
    """Return TraceServerExporter if GENKIT_TELEMETRY_SERVER is set, else None."""
    url = os.environ.get('GENKIT_TELEMETRY_SERVER')
    if not url:
        logger.warn(
            'GENKIT_TELEMETRY_SERVER is not set. If running with `genkit start`, make sure `genkit-cli` is up to date.'
        )
        return None
    return TraceServerExporter(telemetry_server_url=url)


def create_span_processor(exporter: SpanExporter) -> SpanProcessor:
    """RealtimeSpanProcessor in dev, BatchSpanProcessor in production."""
    if is_dev_environment():
        return RealtimeSpanProcessor(exporter)
    return BatchSpanProcessor(exporter)
