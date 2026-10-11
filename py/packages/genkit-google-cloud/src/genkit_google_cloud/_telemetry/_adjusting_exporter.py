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

"""Adjusting trace exporter for PII redaction and span enhancement."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, ClassVar

from genkit_otel import CONTENT_ATTRIBUTES
from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util.types import Attributes, AttributeValue
from typing_extensions import override

# Cloud Trace and the Dev UI read these exact wire keys.
INPUT = 'genkit:input'
OUTPUT = 'genkit:output'
# Anyone with the Cloud project can open the trace, so prompt text,
# replies, system instructions, and tool arguments never leave this
# exporter. A key the span never wrote stays absent.
# Genkit's OTel spans use genkit.input / genkit.output. The colon and slash
# forms are for spans other code writes; _normalize_labels runs after this,
# so keys match with '/' read as ':'.
TRACE_CONTENT_KEYS = frozenset({
    *CONTENT_ATTRIBUTES,
    INPUT,
    OUTPUT,
    # This exporter sits on the process TracerProvider, so it also sees
    # spans from other instrumentations. These and TRACE_CONTENT_PREFIXES
    # are the content keys of the deprecated GenAI spec, OpenInference, and
    # OpenLLMetry. Another library's own keys still pass through.
    'input.value',
    'output.value',
    'traceloop.entity.input',
    'traceloop.entity.output',
})
# Matched as the key itself or the key plus '.<anything>':
# gen_ai.prompt.0.content, llm.input_messages.0.message.content.
TRACE_CONTENT_PREFIXES = (
    'gen_ai.prompt',
    'gen_ai.completion',
    'llm.input_messages',
    'llm.output_messages',
    'llm.prompts',
)
# An exception event's message and stack trace end in str(exc), which can
# quote the prompt (a ValidationError's input_value, say). exception.type stays.
EXCEPTION_EVENT = 'exception'
EXCEPTION_CONTENT_KEYS = ('exception.message', 'exception.stacktrace')
NAME = 'genkit:name'
PATH = 'genkit:path'
IS_ROOT = 'genkit:isRoot'
IS_FAILURE_SOURCE = 'genkit:isFailureSource'
FAILED_SPAN = 'genkit:failedSpan'
FAILED_PATH = 'genkit:failedPath'
FEATURE = 'genkit:feature'
MODEL = 'genkit:model'
SUBTYPE = 'genkit:metadata:subtype'
SUBTYPE_MODEL = 'model'


def is_trace_content_key(key: str) -> bool:
    """True when Cloud Trace must not store the value under ``key``."""
    if key.replace('/', ':') in TRACE_CONTENT_KEYS:
        return True
    return any(key == prefix or key.startswith(prefix + '.') for prefix in TRACE_CONTENT_PREFIXES)


def _copy_attrs(span: ReadableSpan) -> dict[str, AttributeValue]:
    """Return a mutable copy of span attributes."""
    return dict(span.attributes) if span.attributes else {}


class RedactedSpan(ReadableSpan):
    """A span wrapper that overrides attributes, and optionally status and events."""

    # pyrefly:ignore[bad-override]
    _attributes: dict[str, AttributeValue]

    def __init__(
        self,
        span: ReadableSpan,
        attributes: dict[str, AttributeValue],
        *,
        status: Status | None = None,
        events: Sequence[Event] | None = None,
    ) -> None:
        self._span = span
        self._attributes = attributes
        # Unset fields fall through __getattr__ to the wrapped span.
        if status is not None:
            self._status = status
        if events is not None:
            self._events = events

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        return getattr(self._span, name)

    @property
    def attributes(self) -> Attributes:
        """The modified attributes."""
        return self._attributes

    @property
    def dropped_events(self) -> int:
        """Events the SDK dropped on the wrapped span; replacing events keeps the count."""
        return self._span.dropped_events


class AdjustingTraceExporter(SpanExporter):
    """Wraps a SpanExporter to redact PII and enhance spans for cloud plugins (GCP, AWS)."""

    REDACTED: ClassVar[str] = '<redacted>'

    def __init__(
        self,
        exporter: SpanExporter,
        error_handler: Callable[[Exception], None] | None = None,
    ) -> None:
        self._exporter = exporter
        self._error_handler = error_handler

    @override
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        adjusted = [self._adjust(span) for span in spans]
        try:
            return self._exporter.export(adjusted)
        except Exception as e:
            if self._error_handler:
                self._error_handler(e)
            raise

    @override
    def shutdown(self) -> None:
        self._exporter.shutdown()

    @override
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        if hasattr(self._exporter, 'force_flush'):
            return self._exporter.force_flush(timeout_millis)
        return True

    def _adjust(self, span: ReadableSpan) -> ReadableSpan:
        """Apply all adjustments to a span."""
        span = self._redact_pii(span)
        span = self._mark_error(span)
        span = self._mark_failure_source(span)
        span = self._mark_feature(span)
        span = self._mark_model(span)
        span = self._normalize_labels(span)
        return span

    def _redact_pii(self, span: ReadableSpan) -> ReadableSpan:
        attrs = _copy_attrs(span)
        keys_to_redact = [key for key in attrs if is_trace_content_key(key)]
        status = self._redact_status(span.status)
        events = self._redact_events(span.events)
        if not keys_to_redact and status is None and events is None:
            return span
        for key in keys_to_redact:
            attrs[key] = self.REDACTED
        return RedactedSpan(span, attrs, status=status, events=events)

    def _redact_status(self, status: Status | None) -> Status | None:
        """Blank the status description; GenAiInstrumentation sets it to str(exc)."""
        if status is None or not isinstance(status.description, str) or not status.description:
            return None
        return Status(status.status_code, self.REDACTED)

    def _redact_events(self, events: Sequence[Event] | None) -> list[Event] | None:
        """Blank content keys on every event and the message and stack trace on exception events."""
        if not events:
            return None
        redacted: list[Event] = []
        changed = False
        for event in events:
            attrs = dict(event.attributes) if event.attributes else {}
            keys = [key for key in attrs if is_trace_content_key(key)]
            if event.name == EXCEPTION_EVENT:
                keys.extend(key for key in EXCEPTION_CONTENT_KEYS if key in attrs)
            if not keys:
                redacted.append(event)
                continue
            for key in keys:
                attrs[key] = self.REDACTED
            redacted.append(Event(event.name, attrs, event.timestamp))
            changed = True
        return redacted if changed else None

    def _mark_error(self, span: ReadableSpan) -> ReadableSpan:
        if not span.status or span.status.status_code != StatusCode.ERROR:
            return span
        attrs = _copy_attrs(span)
        attrs['/http/status_code'] = '599'
        return RedactedSpan(span, attrs)

    def _mark_failure_source(self, span: ReadableSpan) -> ReadableSpan:
        attrs = _copy_attrs(span)
        if not attrs.get(IS_FAILURE_SOURCE):
            return span
        attrs[FAILED_SPAN] = attrs.get(NAME, '')
        attrs[FAILED_PATH] = attrs.get(PATH, '')
        return RedactedSpan(span, attrs)

    def _mark_feature(self, span: ReadableSpan) -> ReadableSpan:
        attrs = _copy_attrs(span)
        if not attrs.get(IS_ROOT) or not attrs.get(NAME):
            return span
        attrs[FEATURE] = attrs[NAME]
        return RedactedSpan(span, attrs)

    def _mark_model(self, span: ReadableSpan) -> ReadableSpan:
        attrs = _copy_attrs(span)
        if attrs.get(SUBTYPE) != SUBTYPE_MODEL or not attrs.get(NAME):
            return span
        attrs[MODEL] = attrs[NAME]
        return RedactedSpan(span, attrs)

    def _normalize_labels(self, span: ReadableSpan) -> ReadableSpan:
        attrs = _copy_attrs(span)
        normalized = {k.replace(':', '/'): v for k, v in attrs.items()}
        return RedactedSpan(span, normalized)
