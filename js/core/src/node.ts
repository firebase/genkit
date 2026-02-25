/**
 * Copyright 2025 Google LLC
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

import { getGenkitRuntimeConfig } from './config.js';
import { initNodeAsyncContext } from './node-async-context.js';
import {
  setTelemetryProvider,
  setTelemetryProviderInitializer,
} from './tracing.js';
import { initNodeTelemetryProvider } from './tracing/node-telemetry-provider.js';

export { initNodeTelemetryProvider };

/**
 * Node-specific runtime setup (e.g. async_hooks for context propagation).
 */
export function initNodeFeatures() {
  initNodeAsyncContext();
}

/**
 * Ensures a telemetry provider is set: uses config.telemetry if set,
 * otherwise the default Node provider. Called lazily when telemetry is first needed.
 */
function ensureTelemetryProvider() {
  const config = getGenkitRuntimeConfig();
  if (config.telemetry) {
    setTelemetryProvider(config.telemetry);
    return;
  }
  initNodeTelemetryProvider();
}

// Register so that any code path that loads core/node gets the initializer.
// This ensures telemetry works even when reflection or other core code runs before the genkit package has finished loading.
setTelemetryProviderInitializer(ensureTelemetryProvider);
