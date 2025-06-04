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

import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';
import { isDevEnv } from 'genkit';
import type {
  GcpTelemetryConfig,
  GcpTelemetryConfigOptions,
} from '../types.js';

/** Consolidated defaults for telemetry configuration. */

export const TelemetryConfigs = {
  defaults: (overrides: GcpTelemetryConfigOptions = {}): GcpTelemetryConfig => {
    return isDevEnv()
      ? TelemetryConfigs.developmentDefaults(overrides)
      : TelemetryConfigs.productionDefaults(overrides);
  },

  developmentDefaults: (
    overrides: GcpTelemetryConfigOptions = {}
  ): GcpTelemetryConfig => {
    const defaults = {
      sampler: new AlwaysOnSampler(),
      autoInstrumentation: true,
      autoInstrumentationConfig: {
        '@opentelemetry/instrumentation-dns': { enabled: false },
      },
      instrumentations: [],
      metricExportIntervalMillis: 5_000,
      metricExportTimeoutMillis: 5_000,
      disableMetrics: false,
      disableTraces: false,
      exportInputAndOutput: !overrides.disableLoggingInputAndOutput,
      export: !!overrides.forceDevExport, // false
    };
    return { ...defaults, ...overrides };
  },

  productionDefaults: (
    overrides: GcpTelemetryConfigOptions = {}
  ): GcpTelemetryConfig => {
    const defaults = {
      sampler: new AlwaysOnSampler(),
      autoInstrumentation: true,
      autoInstrumentationConfig: {
        '@opentelemetry/instrumentation-dns': { enabled: false },
      },
      instrumentations: [],
      metricExportIntervalMillis: 300_000,
      metricExportTimeoutMillis: 300_000,
      disableMetrics: false,
      disableTraces: false,
      exportInputAndOutput: !overrides.disableLoggingInputAndOutput,
      export: true,
    };
    return { ...defaults, ...overrides };
  },
};
