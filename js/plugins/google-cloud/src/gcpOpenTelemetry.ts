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

import { TelemetryConfig } from '@genkit-ai/core';
import { MetricExporter } from '@google-cloud/opentelemetry-cloud-monitoring-exporter';
import { TraceExporter } from '@google-cloud/opentelemetry-cloud-trace-exporter';
import { GcpDetectorSync } from '@google-cloud/opentelemetry-resource-util';
import { Span, SpanStatusCode, TraceFlags } from '@opentelemetry/api';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { ExportResult } from '@opentelemetry/core';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';
import { WinstonInstrumentation } from '@opentelemetry/instrumentation-winston';
import { Resource } from '@opentelemetry/resources';
import {
  AggregationTemporality,
  InMemoryMetricExporter,
  PeriodicExportingMetricReader,
  PushMetricExporter,
} from '@opentelemetry/sdk-metrics';
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import {
  AlwaysOnSampler,
  BatchSpanProcessor,
  InMemorySpanExporter,
  ReadableSpan,
  SpanExporter,
} from '@opentelemetry/sdk-trace-base';
import { PluginOptions } from './index.js';

let metricExporter: PushMetricExporter;
let metricReader: PeriodicExportingMetricReader;

/**
 * Provides a {TelemetryConfig} for exporting OpenTelemetry data (Traces,
 * Metrics, and Logs) to the Google Cloud Operations Suite.
 */
export class GcpOpenTelemetry implements TelemetryConfig {
  private readonly options: PluginOptions;
  private readonly resource: Resource;

  /**
   * Adjusts spans before exporting to GCP. In particular, redacts PII
   * (input prompts and outputs), and adds a workaround attribute to
   * error spans that marks them as error in GCP.
   */
  private AdjustingTraceExporter = class extends TraceExporter {
    export(
      spans: ReadableSpan[],
      resultCallback: (result: ExportResult) => void
    ): Promise<void> {
      return super.export(this.adjust(spans), resultCallback);
    }

    private adjust(spans: ReadableSpan[]): ReadableSpan[] {
      return spans.map((span) => {
        span = this.redactPii(span);
        span = this.markErrorSpanAsError(span);
        return span;
      });
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
  };

  /**
   * Log hook for writing trace and span metadata to log messages in the format
   * required by GCP.
   */
  private gcpTraceLogHook = (span: Span, record: any) => {
    const isSampled = !!(span.spanContext().traceFlags & TraceFlags.SAMPLED);
    record['logging.googleapis.com/trace'] = `projects/${
      this.options.projectId
    }/traces/${span.spanContext().traceId}`;
    record['logging.googleapis.com/spanId'] = span.spanContext().spanId;
    record['logging.googleapis.com/trace_sampled'] = isSampled ? '1' : '0';
  };

  constructor(options?: PluginOptions) {
    this.options = options || {};
    this.resource = new Resource({ type: 'global' }).merge(
      new GcpDetectorSync().detect()
    );
  }

  getConfig(): Partial<NodeSDKConfiguration> {
    const exporter: SpanExporter = this.shouldExport()
      ? new this.AdjustingTraceExporter()
      : new InMemorySpanExporter();
    metricReader = this.createMetricReader();
    return {
      resource: this.resource,
      spanProcessor: new BatchSpanProcessor(exporter),
      sampler: this.options?.telemetryConfig?.sampler || new AlwaysOnSampler(),
      instrumentations: this.getInstrumentations(),
      metricReader: metricReader,
    };
  }

  /**
   * Creates a {MetricReader} for pushing metrics out to GCP via OpenTelemetry.
   */
  private createMetricReader(): PeriodicExportingMetricReader {
    const shouldExport = this.shouldExport();
    metricExporter = this.shouldExport()
      ? new MetricExporter({ projectId: this.options.projectId })
      : new InMemoryMetricExporter(AggregationTemporality.CUMULATIVE);
    return new PeriodicExportingMetricReader({
      exportIntervalMillis:
        this.options?.telemetryConfig?.metricExportIntervalMillis || 10_000,
      exportTimeoutMillis:
        this.options?.telemetryConfig?.metricExportTimeoutMillis || 10_000,
      exporter: metricExporter,
    });
  }

  /** Gets all open telemetry instrumentations as configured by the plugin. */
  private getInstrumentations() {
    if (this.options?.telemetryConfig?.autoInstrumentation) {
      return getNodeAutoInstrumentations(
        this.options?.telemetryConfig?.autoInstrumentationConfig || {}
      ).concat(this.getDefaultLoggingInstrumentations());
    }
    return this.getDefaultLoggingInstrumentations();
  }

  private shouldExport(): boolean {
    return this.options.forceDevExport || process.env.GENKIT_ENV !== 'dev';
  }

  /** Always configure the Pino and Winston instrumentations */
  private getDefaultLoggingInstrumentations(): Instrumentation[] {
    return [
      new WinstonInstrumentation({ logHook: this.gcpTraceLogHook }),
      new PinoInstrumentation({ logHook: this.gcpTraceLogHook }),
    ];
  }
}

export function __getMetricExporterForTesting(): InMemoryMetricExporter {
  return metricExporter as InMemoryMetricExporter;
}
