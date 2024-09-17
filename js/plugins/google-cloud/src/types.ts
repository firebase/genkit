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

import { InstrumentationConfigMap } from '@opentelemetry/auto-instrumentations-node';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { Sampler } from '@opentelemetry/sdk-trace-base';
import { JWTInput } from 'google-auth-library';

/** Configuration options for the Google Cloud plugin. */
export interface GcpPluginOptions {
  /** Cloud projectId is required, either passed here, through GCLOUD_PROJECT or application default credentials. */
  projectId?: string;

  /** Telemetry configuration overrides. Defaults will be provided depending on the Genkit environment. */
  telemetryConfig?: GcpTelemetryConfigOptions;

  /** Credentials must be provided to export telemetry, if not available through the environment. */
  credentials?: JWTInput;
}

/** Telemetry configuration options. */
export interface GcpTelemetryConfigOptions {
  /** Trace sampler, defaults to always on which exports all traces. */
  sampler?: Sampler;

  /** Include OpenTelemetry autoInstrumentation. Defaults to true. */
  autoInstrumentation?: boolean;
  autoInstrumentationConfig?: InstrumentationConfigMap;
  instrumentations?: Instrumentation[];

  /** Metric export intervals, minimum is 5000ms. */
  metricExportIntervalMillis?: number;
  metricExportTimeoutMillis?: number;

  /** When true, metrics are not exported. */
  disableMetrics?: boolean;

  /** When true, traces are not exported. */
  disableTraces?: boolean;

  /** When true, inputs and outputs are not logged to GCP */
  disableLoggingIO?: boolean;

  /** When true, telemetry data will be exported, even for local runs. Defaults to not exporting development traces. */
  forceDevExport?: boolean;
}

/**
 * Internal telemetry configuration.
 */
export interface GcpTelemetryConfig {
  sampler: Sampler;
  autoInstrumentation: boolean;
  autoInstrumentationConfig: InstrumentationConfigMap;
  metricExportIntervalMillis: number;
  metricExportTimeoutMillis: number;
  instrumentations: Instrumentation[];
  disableMetrics: boolean;
  disableTraces: boolean;
  exportIO: boolean;
  export: boolean;
}

/**
 * Internal configuration for the plugin.
 */
export interface GcpPluginConfig {
  projectId?: string;
  telemetry: GcpTelemetryConfig;
  credentials?: JWTInput;
}
