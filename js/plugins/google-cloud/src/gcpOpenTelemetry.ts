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

import { GENKIT_VERSION, TelemetryConfig } from '@genkit-ai/core';
import { MetricExporter } from '@google-cloud/opentelemetry-cloud-monitoring-exporter';
import { TraceExporter } from '@google-cloud/opentelemetry-cloud-trace-exporter';
import { GcpDetectorSync } from '@google-cloud/opentelemetry-resource-util';
import { Span, SpanStatusCode, TraceFlags } from '@opentelemetry/api';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import {
  ExportResult,
  hrTimeDuration,
  hrTimeToMilliseconds,
} from '@opentelemetry/core';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';
import { WinstonInstrumentation } from '@opentelemetry/instrumentation-winston';
import { Resource } from '@opentelemetry/resources';
import {
  AggregationTemporality,
  DefaultAggregation,
  ExponentialHistogramAggregation,
  InMemoryMetricExporter,
  InstrumentType,
  PeriodicExportingMetricReader,
  PushMetricExporter,
} from '@opentelemetry/sdk-metrics';
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import {
  BatchSpanProcessor,
  InMemorySpanExporter,
  ReadableSpan,
  SpanExporter,
} from '@opentelemetry/sdk-trace-base';

import { extractErrorName } from './utils';

import { PathMetadata } from '@genkit-ai/core/tracing';
import { actionTelemetry } from './telemetry/action.js';
import { flowsTelemetry } from './telemetry/flow.js';
import { generateTelemetry } from './telemetry/generate.js';
import { GcpPluginConfig } from './types';

let metricExporter: PushMetricExporter;
let spanProcessor: BatchSpanProcessor;
let spanExporter: AdjustingTraceExporter;

/**
 * Provides a {TelemetryConfig} for exporting OpenTelemetry data (Traces,
 * Metrics, and Logs) to the Google Cloud Operations Suite.
 */
export class GcpOpenTelemetry implements TelemetryConfig {
  private readonly config: GcpPluginConfig;
  private readonly resource: Resource;

  constructor(config: GcpPluginConfig) {
    this.config = config;
    this.resource = new Resource({ type: 'global' }).merge(
      new GcpDetectorSync().detect()
    );
  }

  /**
   * Log hook for writing trace and span metadata to log messages in the format
   * required by GCP.
   */
  private gcpTraceLogHook = (span: Span, record: any) => {
    const spanContext = span.spanContext();
    const isSampled = !!(spanContext.traceFlags & TraceFlags.SAMPLED);
    const projectId = this.config.projectId;

    record['logging.googleapis.com/trace'] ??=
      `projects/${projectId}/traces/${spanContext.traceId}`;
    record['logging.googleapis.com/trace_sampled'] ??= isSampled ? '1' : '0';
    record['logging.googleapis.com/spanId'] ??= spanContext.spanId;
  };

  getConfig(): Partial<NodeSDKConfiguration> {
    spanProcessor = new BatchSpanProcessor(this.createSpanExporter());
    return {
      resource: this.resource,
      spanProcessor: spanProcessor,
      sampler: this.config.telemetry.sampler,
      instrumentations: this.getInstrumentations(),
      metricReader: this.createMetricReader(),
    };
  }

  private createSpanExporter(): SpanExporter {
    spanExporter = new AdjustingTraceExporter(
      this.shouldExportTraces()
        ? new TraceExporter({
            credentials: this.config.credentials,
          })
        : new InMemorySpanExporter(),
      this.config.telemetry.exportIO,
      this.config.projectId
    );
    return spanExporter;
  }

  /**
   * Creates a {MetricReader} for pushing metrics out to GCP via OpenTelemetry.
   */
  private createMetricReader(): PeriodicExportingMetricReader {
    metricExporter = this.buildMetricExporter();
    return new PeriodicExportingMetricReader({
      exportIntervalMillis: this.config.telemetry.metricExportIntervalMillis,
      exportTimeoutMillis: this.config.telemetry.metricExportTimeoutMillis,
      exporter: metricExporter,
    });
  }

  /** Gets all open telemetry instrumentations as configured by the plugin. */
  private getInstrumentations() {
    if (this.config.telemetry.autoInstrumentation) {
      return getNodeAutoInstrumentations(
        this.config.telemetry.autoInstrumentationConfig
      ).concat(this.getDefaultLoggingInstrumentations());
    }
    return this.getDefaultLoggingInstrumentations();
  }

  private shouldExportTraces(): boolean {
    return this.config.telemetry.export && !this.config.telemetry.disableTraces;
  }

  private shouldExportMetrics(): boolean {
    return (
      this.config.telemetry.export && !this.config.telemetry.disableMetrics
    );
  }

  /** Always configure the Pino and Winston instrumentations */
  private getDefaultLoggingInstrumentations(): Instrumentation[] {
    return [
      new WinstonInstrumentation({ logHook: this.gcpTraceLogHook }),
      new PinoInstrumentation({ logHook: this.gcpTraceLogHook }),
    ];
  }

  private buildMetricExporter(): PushMetricExporter {
    const exporter: PushMetricExporter = this.shouldExportMetrics()
      ? new MetricExporter({
          projectId: this.config.projectId,
          userAgent: {
            product: 'genkit',
            version: GENKIT_VERSION,
          },
          credentials: this.config.credentials,
        })
      : new InMemoryMetricExporter(AggregationTemporality.DELTA);
    exporter.selectAggregation = (instrumentType: InstrumentType) => {
      if (instrumentType === InstrumentType.HISTOGRAM) {
        return new ExponentialHistogramAggregation();
      }
      return new DefaultAggregation();
    };
    exporter.selectAggregationTemporality = (
      instrumentType: InstrumentType
    ) => {
      return AggregationTemporality.DELTA;
    };
    return exporter;
  }
}

/**
 * Adjusts spans before exporting to GCP. In particular, redacts PII
 * (input prompts and outputs), and adds a workaround attribute to
 * error spans that marks them as error in GCP.
 */
class AdjustingTraceExporter implements SpanExporter {
  constructor(
    private exporter: SpanExporter,
    private logIO: boolean,
    private projectId?: string
  ) {}

  export(
    spans: ReadableSpan[],
    resultCallback: (result: ExportResult) => void
  ): void {
    this.exporter?.export(this.adjust(spans), resultCallback);
  }

  shutdown(): Promise<void> {
    return this.exporter?.shutdown();
  }

  getExporter(): SpanExporter {
    return this.exporter;
  }

  forceFlush(): Promise<void> {
    if (this.exporter?.forceFlush) {
      return this.exporter.forceFlush();
    }
    return Promise.resolve();
  }

  private adjust(spans: ReadableSpan[]): ReadableSpan[] {
    const allPaths = spans
      .filter((span) => span.attributes['genkit:path'])
      .map(
        (span) =>
          ({
            path: span.attributes['genkit:path'] as string,
            status:
              (span.attributes['genkit:state'] as string) === 'error'
                ? 'failure'
                : 'success',
            error: extractErrorName(span.events),
            latency: hrTimeToMilliseconds(
              hrTimeDuration(span.startTime, span.endTime)
            ),
          }) as PathMetadata
      );

    const allLeafPaths = new Set<PathMetadata>(
      allPaths.filter((leafPath) =>
        allPaths.every(
          (path) =>
            path.path === leafPath.path ||
            !path.path.startsWith(leafPath.path) ||
            (path.path.startsWith(leafPath.path) &&
              path.status !== leafPath.status)
        )
      )
    );

    return spans.map((span) => {
      this.tickTelemetry(span, allLeafPaths);

      span = this.redactPii(span);
      span = this.markErrorSpanAsError(span);
      span = this.normalizeLabels(span);
      return span;
    });
  }

  private tickTelemetry(span: ReadableSpan, paths: Set<PathMetadata>) {
    const attributes = span.attributes;

    if (!Object.keys(attributes).includes('genkit:type')) {
      return;
    }

    const type = attributes['genkit:type'] as string;
    const subtype = attributes['genkit:metadata:subtype'] as string;

    if (type === 'flow') {
      flowsTelemetry.tick(span, paths, this.logIO, this.projectId);
      return;
    }

    if (type === 'action' && subtype === 'model') {
      generateTelemetry.tick(span, paths, this.logIO, this.projectId);
      return;
    }

    if (type === 'action' || type == 'flowStep') {
      actionTelemetry.tick(span, paths, this.logIO, this.projectId);
    }
  }

  private redactPii(span: ReadableSpan): ReadableSpan {
    const hasInput = 'genkit:input' in span.attributes;
    const hasOutput = 'genkit:output' in span.attributes;

    return !hasInput && !hasOutput
      ? span
      : {
          ...span,
          spanContext: span.spanContext,
          attributes: {
            ...span.attributes,
            'genkit:input': '<redacted>',
            'genkit:output': '<redacted>',
          },
        };
  }

  // This is a workaround for GCP Trace to mark a span with a red
  // exclamation mark indicating that it is an error.
  private markErrorSpanAsError(span: ReadableSpan): ReadableSpan {
    return span.status.code !== SpanStatusCode.ERROR
      ? span
      : {
          ...span,
          spanContext: span.spanContext,
          attributes: {
            ...span.attributes,
            '/http/status_code': '599',
          },
        };
  }

  // This is a workaround for GCP Trace to mark a span with a red
  // exclamation mark indicating that it is an error.
  private normalizeLabels(span: ReadableSpan): ReadableSpan {
    const normalized = {} as Record<string, any>;
    for (const [key, value] of Object.entries(span.attributes)) {
      normalized[key.replace(/\:/g, '/')] = value;
    }
    return {
      ...span,
      spanContext: span.spanContext,
      attributes: normalized,
    };
  }
}

export function __getMetricExporterForTesting(): InMemoryMetricExporter {
  return metricExporter as InMemoryMetricExporter;
}

export function __getSpanExporterForTesting(): InMemorySpanExporter {
  return spanExporter.getExporter() as InMemorySpanExporter;
}

export function __forceFlushSpansForTesting() {
  spanProcessor.forceFlush();
}
