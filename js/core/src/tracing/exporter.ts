/**
 * Copyright 2024 Google LLC
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

import { context, SpanKind, type HrTime } from '@opentelemetry/api';
import {
  ExportResultCode,
  hrTimeToMilliseconds,
  suppressTracing,
  type ExportResult,
} from '@opentelemetry/core';
import type { ReadableSpan, SpanExporter } from '@opentelemetry/sdk-trace-base';
import { logger } from '../logging.js';
import { deleteUndefinedProps } from '../utils.js';
import type { SpanData, TraceData } from './types.js';

export let telemetryServerUrl: string | undefined;
export let telemetryServerHeaders: Record<string, string> | undefined;

/**
 * Configuration for the telemetry server used by TraceServerExporter.
 * @hidden
 */
export interface TelemetryServerConfig {
  url?: string;
  headers?: Record<string, string>;
}

/**
 * Set telemetry server URL and/or headers in one call.
 * @hidden
 */
export function setTelemetryServerConfig(config: TelemetryServerConfig) {
  if (config.url !== undefined) {
    telemetryServerUrl = config.url;
  }
  if (config.headers !== undefined) {
    telemetryServerHeaders =
      Object.keys(config.headers).length > 0 ? config.headers : undefined;
  }
}

/**
 * Exports collected OpenTelemetetry spans to the telemetry server.
 */
export class TraceServerExporter implements SpanExporter {
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
      attributes: { ...span.attributes },
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
    let error = false;
    for (const traceId of Object.keys(traces)) {
      try {
        await this.save(traceId, traces[traceId]);
      } catch (e) {
        error = true;
        logger.error(`Failed to save trace ${traceId}`, e);
      }
      if (done) {
        return done({
          code: error ? ExportResultCode.FAILED : ExportResultCode.SUCCESS,
        });
      }
    }
  }

  private async save(traceId, spans: ReadableSpan[]): Promise<void> {
    if (!telemetryServerUrl) {
      logger.debug(
        `Telemetry server is not configured, trace ${traceId} not saved!`
      );
      return;
    }
    // TODO: add interface for Firestore doc
    const data = {
      traceId,
      spans: {},
    } as TraceData;
    for (const span of spans) {
      const convertedSpan = this._exportInfo(span);
      data.spans[convertedSpan.spanId] = convertedSpan;
      if (!convertedSpan.parentSpanId) {
        data.displayName = convertedSpan.displayName;
        data.startTime = convertedSpan.startTime;
        data.endTime = convertedSpan.endTime;
      }
    }

    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...telemetryServerHeaders,
    };
    // Suppress tracing to prevent infinite loops when auto-instrumentation
    // (e.g., undici) is enabled. Without this, the fetch call would be traced,
    // creating new spans that trigger more exports, causing stack overflow.
    await context.with(suppressTracing(context.active()), () =>
      fetch(`${telemetryServerUrl}/api/traces`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      })
    );
  }
}

// Converts an HrTime to milliseconds.
function transformTime(time: HrTime) {
  return hrTimeToMilliseconds(time);
}
