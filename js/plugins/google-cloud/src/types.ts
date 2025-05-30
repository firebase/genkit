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

import type { InstrumentationConfigMap } from '@opentelemetry/auto-instrumentations-node';
import type { Instrumentation } from '@opentelemetry/instrumentation';
import type { Sampler } from '@opentelemetry/sdk-trace-base';
import type { JWTInput } from 'google-auth-library';

/** Configuration options for the Google Cloud plugin. */
export interface GcpTelemetryConfigOptions {
  /**
   * Google Cloud Project ID. If provided, will take precedence over the
   * projectId inferred from the application credential and/or environment.
   * Required when providing an external credential (e.g. Workload Identity
   * Federation.)
   */
  projectId?: string;

  /**
   * Credentials for authenticating with Google Cloud. Primarily intended for
   * use in environments outside of GCP. On GCP credentials will typically be
   * inferred from the environment via Application Default Credentials (ADC).
   */
  credentials?: JWTInput;

  /**
   * OpenTelemetry sampler; controls the number of traces collected and exported
   * to Google Cloud. Defaults to AlwaysOnSampler, which will collect and export
   * all traces.
   *
   * There are four built-in samplers to choose from:
   *
   * - {@link https://github.com/open-telemetry/opentelemetry-js/blob/main/packages/opentelemetry-sdk-trace-base/src/sampler/AlwaysOnSampler.ts | AlwaysOnSampler} - samples all traces
   * - {@link https://github.com/open-telemetry/opentelemetry-js/blob/main/packages/opentelemetry-sdk-trace-base/src/sampler/AlwaysOffSampler.ts | AlwaysOffSampler} - samples no traces
   * - {@link https://github.com/open-telemetry/opentelemetry-js/blob/main/packages/opentelemetry-sdk-trace-base/src/sampler/ParentBasedSampler.ts | ParentBasedSampler} - samples based on parent span
   * - {@link https://github.com/open-telemetry/opentelemetry-js/blob/main/packages/opentelemetry-sdk-trace-base/src/sampler/TraceIdRatioBasedSampler.ts | TraceIdRatioBasedSampler} - samples a configurable percentage of traces
   */
  sampler?: Sampler;

  /**
   * Enabled by default, OpenTelemetry will automatically collect telemetry for
   * popular libraries via auto instrumentations without any additional code
   * or configuration. All available instrumentations will be collected, unless
   * otherwise specified via {@link autoInstrumentationConfig}.
   *
   * @see https://opentelemetry.io/docs/zero-code/js/
   */
  autoInstrumentation?: boolean;

  /**
   * Map of auto instrumentations and their configuration options. Available
   * options will vary by instrumentation.
   *
   * @see https://opentelemetry.io/docs/zero-code/js/
   */
  autoInstrumentationConfig?: InstrumentationConfigMap;

  /**
   * Additional OpenTelemetry instrumentations to include, beyond those
   * provided by auto instrumentations.
   */
  instrumentations?: Instrumentation[];

  /**
   * Metrics export interval in milliseconds; Google Cloud requires a minimum
   * value of 5000ms.
   */
  metricExportIntervalMillis?: number;

  /**
   * Timeout for the metrics export in milliseconds.
   */
  metricExportTimeoutMillis?: number;

  /**
   * If set to true, metrics will not be exported to Google Cloud. Traces and
   * logs may still be exported.
   */
  disableMetrics?: boolean;

  /**
   * If set to true, traces will not be exported to Google Cloud. Metrics and
   * logs may still be exported.
   */
  disableTraces?: boolean;

  /**
   * If set to true, input and output logs will not be collected.
   */
  disableLoggingInputAndOutput?: boolean;

  /**
   * If set to true, telemetry data will be exported in the Genkit `dev`
   * environment. Useful for local testing and troubleshooting; default is
   * false.
   */
  forceDevExport?: boolean;
}

/** Internal telemetry configuration. */
export interface GcpTelemetryConfig {
  projectId?: string;
  credentials?: JWTInput;

  sampler: Sampler;
  autoInstrumentation: boolean;
  autoInstrumentationConfig: InstrumentationConfigMap;
  metricExportIntervalMillis: number;
  metricExportTimeoutMillis: number;
  instrumentations: Instrumentation[];
  disableMetrics: boolean;
  disableTraces: boolean;
  exportInputAndOutput: boolean;
  export: boolean;
}

export interface GcpPrincipal {
  projectId?: string;
  serviceAccountEmail?: string;
}
