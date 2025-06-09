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

import { NodeSDK } from '@opentelemetry/sdk-node';
import {
  BatchSpanProcessor,
  SimpleSpanProcessor,
  type SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import { logger } from './logging.js';
import type { TelemetryConfig } from './telemetryTypes.js';
import {
  TraceServerExporter,
  setTelemetryServerUrl,
} from './tracing/exporter.js';
import { isDevEnv } from './utils.js';

export * from './tracing/exporter.js';
export * from './tracing/instrumentation.js';
export * from './tracing/processor.js';
export * from './tracing/types.js';

let telemetrySDK: NodeSDK | null = null;
let nodeOtelConfig: TelemetryConfig | null = null;

const instrumentationKey = '__GENKIT_TELEMETRY_INSTRUMENTED';

/**
 * @hidden
 */
export async function ensureBasicTelemetryInstrumentation() {
  await checkFirebaseMonitoringAutoInit();

  if (global[instrumentationKey]) {
    return await global[instrumentationKey];
  }

  await enableTelemetry({});
}

/**
 * Checks to see if the customer is using Firebase Genkit Monitoring
 * auto initialization via environment variable by attempting to resolve
 * the firebase plugin.
 *
 * Enables Firebase Genkit Monitoring if the plugin is installed and warns
 * if it hasn't been installed.
 */
async function checkFirebaseMonitoringAutoInit() {
  if (
    !global[instrumentationKey] &&
    process.env.ENABLE_FIREBASE_MONITORING === 'true'
  ) {
    try {
      const firebaseModule = await require('@genkit-ai/firebase');
      firebaseModule.enableFirebaseTelemetry();
    } catch (e) {
      logger.warn(
        "It looks like you're trying to enable firebase monitoring, but " +
          "haven't installed the firebase plugin. Please run " +
          '`npm i --save @genkit-ai/firebase` and redeploy.'
      );
    }
  }
}

/**
 * Enables tracing and metrics open telemetry configuration.
 */
export async function enableTelemetry(
  telemetryConfig: TelemetryConfig | Promise<TelemetryConfig>
) {
  if (process.env.GENKIT_TELEMETRY_SERVER) {
    setTelemetryServerUrl(process.env.GENKIT_TELEMETRY_SERVER);
  }
  global[instrumentationKey] =
    telemetryConfig instanceof Promise ? telemetryConfig : Promise.resolve();

  telemetryConfig =
    telemetryConfig instanceof Promise
      ? await telemetryConfig
      : telemetryConfig;

  nodeOtelConfig = telemetryConfig || {};

  const processors: SpanProcessor[] = [createTelemetryServerProcessor()];
  if (nodeOtelConfig.traceExporter) {
    throw new Error('Please specify spanProcessors instead.');
  }
  if (nodeOtelConfig.spanProcessors) {
    processors.push(...nodeOtelConfig.spanProcessors);
  }
  if (nodeOtelConfig.spanProcessor) {
    processors.push(nodeOtelConfig.spanProcessor);
    delete nodeOtelConfig.spanProcessor;
  }
  nodeOtelConfig.spanProcessors = processors;
  telemetrySDK = new NodeSDK(nodeOtelConfig);
  telemetrySDK.start();
  process.on('SIGTERM', async () => await cleanUpTracing());
}

export async function cleanUpTracing(): Promise<void> {
  if (!telemetrySDK) {
    return;
  }

  // Metrics are not flushed as part of the shutdown operation. If metrics
  // are enabled, we need to manually flush them *before* the reader
  // receives shutdown order.
  await maybeFlushMetrics();
  await telemetrySDK.shutdown();
  logger.debug('OpenTelemetry SDK shut down.');
  telemetrySDK = null;
}

/**
 * Creates a new SpanProcessor for exporting data to the telemetry server.
 */
function createTelemetryServerProcessor(): SpanProcessor {
  const exporter = new TraceServerExporter();
  return isDevEnv()
    ? new SimpleSpanProcessor(exporter)
    : new BatchSpanProcessor(exporter);
}

/** Flush metrics if present. */
function maybeFlushMetrics(): Promise<void> {
  if (nodeOtelConfig?.metricReader) {
    return nodeOtelConfig.metricReader.forceFlush();
  }
  return Promise.resolve();
}

/**
 * Flushes all configured span processors.
 *
 * @hidden
 */
export async function flushTracing() {
  if (nodeOtelConfig?.spanProcessors) {
    await Promise.all(nodeOtelConfig.spanProcessors.map((p) => p.forceFlush()));
  }
}
