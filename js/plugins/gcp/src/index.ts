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

import { genkitPlugin, Plugin } from '@genkit-ai/core/config';
import { InstrumentationConfigMap } from '@opentelemetry/auto-instrumentations-node';
import { Instrumentation } from '@opentelemetry/instrumentation';
import { Sampler } from '@opentelemetry/sdk-trace-base';
import { GcpLogger } from './gcpLogger.js';
import { GcpOpenTelemetry } from './gcpOpenTelemetry.js';

export interface PluginOptions {
  projectId?: string;
  telemetryConfig?: TelemetryConfig;
}

export interface TelemetryConfig {
  sampler?: Sampler;
  autoInstrumentation?: boolean;
  autoInstrumentationConfig?: InstrumentationConfigMap;
  metricExportIntervalMillis?: number;
  instrumentations?: Instrumentation[];
}

/**
 * Provides a plugin for using Genkit with GCP.
 */
export const gcp: Plugin<[PluginOptions]> = genkitPlugin(
  'gcp',
  async (options: PluginOptions) => {
    return {
      telemetry: {
        instrumentation: {
          id: 'gcp',
          value: new GcpOpenTelemetry(options),
        },
        logger: {
          id: 'gcp',
          value: new GcpLogger(options),
        },
      },
    };
  }
);

export default gcp;
