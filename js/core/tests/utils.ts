import { SpanKind } from '@opentelemetry/api';
import { ExportResult } from '@opentelemetry/core';
import { ReadableSpan, SpanExporter } from '@opentelemetry/sdk-trace-base';

export class TestSpanExporter implements SpanExporter {
  exportedSpans: any[] = [];

  export(
    spans: ReadableSpan[],
    resultCallback: (result: ExportResult) => void
  ): void {
    this.exportedSpans.push(...spans.map((s) => this._exportInfo(s)));
    resultCallback({ code: 0 });
  }

  shutdown(): Promise<void> {
    return this.forceFlush();
  }

  private _exportInfo(span: ReadableSpan) {
    return {
      spanId: span.spanContext().spanId,
      traceId: span.spanContext().traceId,
      attributes: { ...span.attributes },
      displayName: span.name,
      links: span.links,
      spanKind: SpanKind[span.kind],
      parentSpanId: span.parentSpanId,
      sameProcessAsParentSpan: { value: !span.spanContext().isRemote },
      status: span.status,
      timeEvents: {
        timeEvent: span.events.map((e) => ({
          annotation: {
            attributes: e.attributes ?? {},
            description: e.name,
          },
        })),
      },
    };
  }
  forceFlush(): Promise<void> {
    return Promise.resolve();
  }
}
