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

import { configureGenkit } from '@genkit-ai/core';
import { firebase } from '@genkit-ai/firebase';
import { googleCloud } from '@genkit-ai/google-cloud';
import { googleAI } from '@genkit-ai/googleai';
import { vertexAI } from '@genkit-ai/vertexai';
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';

export default configureGenkit({
  plugins: [
    firebase(),
    googleAI(),
    vertexAI(),
    googleCloud({
      // Forces telemetry export in 'dev'
      forceDevExport: true,
      // These are configured for demonstration purposes. Sensible defaults are
      // in place in the event that telemetryConfig is absent.
      telemetryConfig: {
        sampler: new AlwaysOnSampler(),
        autoInstrumentation: true,
        autoInstrumentationConfig: {
          '@opentelemetry/instrumentation-fs': { enabled: false },
          '@opentelemetry/instrumentation-dns': { enabled: false },
          '@opentelemetry/instrumentation-net': { enabled: false },
        },
        metricExportIntervalMillis: 5_000,
      },
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'error',
  telemetry: {
    instrumentation: 'googleCloud',
    logger: 'googleCloud',
  },
});
