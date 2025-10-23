/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { SpanData, TraceData } from '@genkit-ai/tools-common';

// These interfaces are based on the OTLP JSON format.
// A full definition can be found at:
// https://github.com/open-telemetry/opentelemetry-proto/blob/main/opentelemetry/proto

interface OtlpValue {
  stringValue?: string;
  intValue?: number;
  boolValue?: boolean;
  arrayValue?: {
    values: OtlpValue[];
  };
}

interface OtlpAttribute {
  key: string;
  value: OtlpValue;
}

interface OtlpSpan {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  name: string;
  kind: number;
  startTimeUnixNano: string;
  endTimeUnixNano: string;
  attributes: OtlpAttribute[];
  droppedAttributesCount: number;
  events: any[];
  droppedEventsCount: number;
  status?: {
    code: number;
    message?: string;
  };
  links: any[];
  droppedLinksCount: number;
}

interface OtlpScopeSpan {
  scope: {
    name: string;
    version: string;
  };
  spans: OtlpSpan[];
}

interface OtlpResourceSpan {
  resource: {
    attributes: OtlpAttribute[];
    droppedAttributesCount: number;
  };
  scopeSpans: OtlpScopeSpan[];
}

interface OtlpPayload {
  resourceSpans: OtlpResourceSpan[];
}

function toMillis(nano: string): number {
  return Math.round(parseInt(nano) / 1_000_000);
}

function toSpanData(span: OtlpSpan, scope: OtlpScopeSpan['scope']): SpanData {
  const attributes: Record<string, any> = {};
  span.attributes.forEach((attr) => {
    if (attr.value.stringValue) {
      attributes[attr.key] = attr.value.stringValue;
    } else if (attr.value.intValue) {
      attributes[attr.key] = attr.value.intValue;
    } else if (attr.value.boolValue) {
      attributes[attr.key] = attr.value.boolValue;
    }
  });

  let spanKind: string;
  switch (span.kind) {
    case 1:
      spanKind = 'INTERNAL';
      break;
    case 2:
      spanKind = 'SERVER';
      break;
    case 3:
      spanKind = 'CLIENT';
      break;
    case 4:
      spanKind = 'PRODUCER';
      break;
    case 5:
      spanKind = 'CONSUMER';
      break;
    default:
      spanKind = 'UNSPECIFIED';
      break;
  }

  const spanData: SpanData = {
    traceId: span.traceId,
    spanId: span.spanId,
    parentSpanId: span.parentSpanId,
    startTime: toMillis(span.startTimeUnixNano),
    endTime: toMillis(span.endTimeUnixNano),
    displayName: span.name,
    attributes,
    instrumentationLibrary: {
      name: scope.name,
      version: scope.version,
    },
    spanKind,
  };
  if (span.status && span.status.code !== 0) {
    const status: { code: number; message?: string } = {
      code: span.status.code,
    };
    if (span.status.message) {
      status.message = span.status.message;
    }
    spanData.status = status;
  }
  return spanData;
}

export function tracesDataFromOtlp(otlpData: OtlpPayload): TraceData[] {
  const traces: Record<string, TraceData> = {};

  otlpData.resourceSpans.forEach((resourceSpan) => {
    resourceSpan.scopeSpans.forEach((scopeSpan) => {
      scopeSpan.spans.forEach((span) => {
        if (!traces[span.traceId]) {
          traces[span.traceId] = {
            traceId: span.traceId,
            spans: {},
          };
        }
        traces[span.traceId].spans[span.spanId] = toSpanData(
          span,
          scopeSpan.scope
        );
      });
    });
  });

  return Object.values(traces);
}
