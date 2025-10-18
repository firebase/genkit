import { SpanData, TraceData } from './trace';

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
  status: {
    code: number;
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

function toSpanData(
  span: OtlpSpan,
  scope: OtlpScopeSpan['scope']
): SpanData {
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

  return {
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
