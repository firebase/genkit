import { Plugin, genkitPlugin } from '@google-genkit/common/config';
import { GcpOpenTelemetry } from './gcpOpenTelemetry';
import { Sampler } from '@opentelemetry/api';
import { AlwaysOnSampler } from '@opentelemetry/core';
import { InstrumentationConfigMap } from '@opentelemetry/auto-instrumentations-node';
export { GcpOpenTelemetry } from './gcpOpenTelemetry';

export interface PluginOptions {
  projectId?: string;
  telemetryConfig?: TelemetryConfig;
}

export interface TelemetryConfig {
  sampler?: Sampler;
  autoInstrumentation?: boolean;
  autoInstrumentationConfig?: InstrumentationConfigMap;
  metricExportIntervalMillis?: number;
}

/**
 * Provides a plugin for using Genkit with GCP.
 */
export const gcp: Plugin<[PluginOptions]> = genkitPlugin(
  'gcp',
  async (options: PluginOptions) => {
    return {
      telemetry: {
        id: 'gcp',
        value: new GcpOpenTelemetry(options),
      },
    };
  }
);

export default gcp;
