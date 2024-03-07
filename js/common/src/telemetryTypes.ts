import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';

/**
 * Provides a {NodeSDKConfiguration} configuration for use with the
 * Open-Telemetry SDK. This configuration allows plugins to specify how and
 * where open telemetry data will be exported.
 */
export interface TelemetryConfig {
  getConfig(): Partial<NodeSDKConfiguration>;
}

/**
 * Options for configuring the Open-Telemetry export configuration as part of a
 * Genkit config file.
 */
export interface TelemetryOptions {
  /**
   * Specifies which telemetry export provider to use. The value specified here
   * must match the id of a {TelemetryConfig} provided by an installed plugin.
   *
   * Note: Telemetry data is only exported when running in the `prod`
   * environment.
   * */
  instrumentation: string;
}
