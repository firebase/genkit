import { SpanKind, HrTime } from '@opentelemetry/api';
import { SpanExporter, ReadableSpan } from '@opentelemetry/sdk-trace-base';
import {
  ExportResult,
  ExportResultCode,
  hrTimeToMicroseconds,
} from '@opentelemetry/core';
import { SpanData, TraceData, TraceStore } from './types.js';
import { deleteUndefinedProps } from '../utils.js';

/**
 * Exports collected OpenTelemetetry spans to Firestore.
 */
export class TraceStoreExporter implements SpanExporter {
  constructor(private traceStore: TraceStore) {}

  /**
   * Export spans.
   * @param spans
   * @param resultCallback
   */
  export(
    spans: ReadableSpan[],
    resultCallback: (result: ExportResult) => void
  ): void {
    this._sendSpans(spans, resultCallback);
  }

  /**
   * Shutdown the exporter.
   */
  shutdown(): Promise<void> {
    this._sendSpans([]);
    return this.forceFlush();
  }

  /**
   * Converts span info into trace store format.
   * @param span
   */
  private _exportInfo(span: ReadableSpan): SpanData {
    const spanData: Partial<SpanData> = {
      spanId: span.spanContext().spanId,
      traceId: span.spanContext().traceId,
      startTime: transformTime(span.startTime),
      endTime: transformTime(span.endTime),
      attributes: span.attributes,
      displayName: span.name,
      links: span.links,
      spanKind: SpanKind[span.kind],
      parentSpanId: span.parentSpanId,
      sameProcessAsParentSpan: { value: !span.spanContext().isRemote },
      status: span.status,
      timeEvents: {
        timeEvent: span.events.map((e) => ({
          time: transformTime(e.time),
          annotation: {
            attributes: e.attributes ?? {},
            description: e.name,
          },
        })),
      },
    };
    if (span.instrumentationLibrary !== undefined) {
      spanData.instrumentationLibrary = {
        name: span.instrumentationLibrary.name,
      };
      if (span.instrumentationLibrary.schemaUrl !== undefined) {
        spanData.instrumentationLibrary.schemaUrl =
          span.instrumentationLibrary.schemaUrl;
      }
      if (span.instrumentationLibrary.version !== undefined) {
        spanData.instrumentationLibrary.version =
          span.instrumentationLibrary.version;
      }
    }
    deleteUndefinedProps(spanData);
    return spanData as SpanData;
  }

  /**
   * Exports any pending spans in exporter
   */
  forceFlush(): Promise<void> {
    return Promise.resolve();
  }

  private async _sendSpans(
    spans: ReadableSpan[],
    done?: (result: ExportResult) => void
  ): Promise<void> {
    const traces = {} as Record<string, ReadableSpan[]>;
    for (const span of spans) {
      if (!traces[span.spanContext().traceId]) {
        traces[span.spanContext().traceId] = [];
      }
      traces[span.spanContext().traceId].push(span);
    }
    for (const traceId of Object.keys(traces)) {
      await this.save(traceId, traces[traceId]);
    }
    if (done) {
      return done({ code: ExportResultCode.SUCCESS });
    }
  }

  private async save(traceId, spans: ReadableSpan[]): Promise<void> {
    // TODO: add interface for Firestore doc
    const data = {
      spans: {},
    } as TraceData;
    for (const span of spans) {
      const conertedSpan = this._exportInfo(span);
      data.spans[conertedSpan.spanId] = conertedSpan;
      if (!conertedSpan.parentSpanId) {
        data.displayName = conertedSpan.displayName;
        data.startTime = conertedSpan.startTime;
        data.endTime = conertedSpan.endTime;
      }
    }
    await this.traceStore.save(traceId, data);
  }
}

function transformTime(time: HrTime) {
  return hrTimeToMicroseconds(time);
}
