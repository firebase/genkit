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

import { GenkitError } from './error.js';
import type { TelemetryConfig } from './telemetryTypes.js';
import { setTelemetryServerUrl } from './tracing/exporter.js';
import { getEnvVar } from './utils.js';

export * from './tracing/exporter.js';
export * from './tracing/instrumentation.js';
export * from './tracing/processor.js';
export * from './tracing/types.js';

const instrumentationKey = '__GENKIT_TELEMETRY_INSTRUMENTED';

export interface GenkitOtel {
  enableTelemetry(telemetryConfig: TelemetryConfig | Promise<TelemetryConfig>);

  shutdown(): Promise<void>;

  flushTracing(): Promise<void>;

  flushMetrics(): Promise<void>;
}

export function _getGenkitOtel(): GenkitOtel {
  const instr = globalThis.__genkit__GenkitOtel;
  if (!instr) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message: 'Failed to find GenkitOtel, probable misconfiguration.',
    });
  }

  return instr;
}

export function _setGenkitOtel(instr: GenkitOtel) {
  globalThis.__genkit__GenkitOtel = instr;
}

/**
 * @hidden
 */
export async function ensureBasicTelemetryInstrumentation() {
  if (globalThis[instrumentationKey]) {
    return await globalThis[instrumentationKey];
  }
  await enableTelemetry({});
}

/**
 * Enables tracing and metrics open telemetry configuration.
 */
export async function enableTelemetry(
  telemetryConfig: TelemetryConfig | Promise<TelemetryConfig>
) {
  if (getEnvVar('GENKIT_TELEMETRY_SERVER')) {
    setTelemetryServerUrl(getEnvVar('GENKIT_TELEMETRY_SERVER')!);
  }
  globalThis[instrumentationKey] =
    telemetryConfig instanceof Promise ? telemetryConfig : Promise.resolve();
  _getGenkitOtel().enableTelemetry(telemetryConfig);
}

export async function cleanUpTracing(): Promise<void> {
  await _getGenkitOtel().shutdown();
}

/**
 * Flushes all configured span processors.
 *
 * @hidden
 */
export async function flushTracing() {
  await _getGenkitOtel().flushTracing();
}
