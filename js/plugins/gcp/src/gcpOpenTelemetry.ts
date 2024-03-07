import { AlwaysOnSampler } from '@opentelemetry/core';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { GcpDetectorSync } from '@google-cloud/opentelemetry-resource-util';
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import { PinoInstrumentation } from '@opentelemetry/instrumentation-pino';
import { Resource } from '@opentelemetry/resources';
import { Span } from '@opentelemetry/api';
import { TelemetryConfig } from '@google-genkit/common';
import { TraceExporter } from '@google-cloud/opentelemetry-cloud-trace-exporter';
import { WinstonInstrumentation } from '@opentelemetry/instrumentation-winston';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { PluginOptions } from './index';

/**
 * Provides a {TelemetryConfig} for exporting OpenTelemetry data (Traces,
 * Metrics, and Logs) to the Google Cloud Operations Suite.
 */
export class GcpOpenTelemetry implements TelemetryConfig {
  private readonly options: PluginOptions;

  constructor(options: PluginOptions) {
    this.options = options;
  }

  getConfig(): Partial<NodeSDKConfiguration> {
    return {
      resource: new Resource({
        type: 'global',
      }).merge(new GcpDetectorSync().detect()),
      spanProcessor: new BatchSpanProcessor(new TraceExporter()) as any,
      sampler: this.options?.telemetryConfig?.sampler || new AlwaysOnSampler(),
      instrumentations: this.getInstrumentations(),
    };
  }

  /** Gets all open telemetry instrumentations as configured by the plugin. */
  private getInstrumentations() {
    if (this.options?.telemetryConfig?.autoInstrumentation) {
      return this.getDefaultLoggingInstrumentations().concat(
        getNodeAutoInstrumentations(
          this.options?.telemetryConfig?.autoInstrumentationConfig || {}
        )
      );
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
