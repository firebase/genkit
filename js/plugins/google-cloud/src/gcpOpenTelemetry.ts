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
import { Span, SpanStatusCode } from '@opentelemetry/api';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { ExportResult } from '@opentelemetry/core';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';
import { WinstonInstrumentation } from '@opentelemetry/instrumentation-winston';
import { Resource } from '@opentelemetry/resources';
import {
  MetricReader,
  PeriodicExportingMetricReader,
} from '@opentelemetry/sdk-metrics';
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import {
  AlwaysOnSampler,
  BatchSpanProcessor,
  ReadableSpan,
} from '@opentelemetry/sdk-trace-base';
import { PluginOptions } from './index';

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

  constructor(options: PluginOptions) {
    this.options = options;
    this.resource = new Resource({ type: 'global' }).merge(
      new GcpDetectorSync().detect()
    );
  }

  getConfig(): Partial<NodeSDKConfiguration> {
    return {
      resource: this.resource,
      spanProcessor: new BatchSpanProcessor(new this.AdjustingTraceExporter()),
      sampler: this.options?.telemetryConfig?.sampler || new AlwaysOnSampler(),
      instrumentations: this.getInstrumentations(),
      metricReader: this.createMetricReader(),
    };
  }

  /**
   * Creates a {MetricReader} for pushing metrics out to GCP via OpenTelemetry.
   */
  private createMetricReader(): MetricReader {
    return new PeriodicExportingMetricReader({
      exportIntervalMillis:
        this.options?.telemetryConfig?.metricExportIntervalMillis || 10_000,
      exporter: new MetricExporter({ projectId: this.options.projectId }),
    }) as MetricReader;
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

  /** Always configure the Pino and Winston instrumentations */
  private getDefaultLoggingInstrumentations(): Instrumentation[] {
    return [
      new WinstonInstrumentation({
        logHook: (span: Span, record: any) => {
          record['logging.googleapis.com/trace'] = `projects/${
            this.options.projectId
          }/traces/${span.spanContext().traceId}`;
          record['logging.googleapis.com/spanId'] = span.spanContext().spanId;
          record['logging.googleapis.com/trace_sampled'] = '1';
        },
      }),
      new PinoInstrumentation({
        logHook: (span: any, record: any) => {
          record['logging.googleapis.com/trace'] = `projects/${
            this.options.projectId
          }/traces/${span.spanContext().traceId}`;
          record['logging.googleapis.com/spanId'] = span.spanContext().spanId;
          record['logging.googleapis.com/trace_sampled'] = '1';
        },
      }),
    ];
  }
}
