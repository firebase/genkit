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
import { GenkitOtel } from './tracing.js';
import {
  TraceServerExporter,
  setTelemetryServerUrl,
} from './tracing/exporter.js';
import { getEnvVar, isDevEnv } from './utils.js';

let telemetrySDK: NodeSDK | null = null;
let nodeOtelConfig: TelemetryConfig | null = null;

export class NodeGenkitOtel implements GenkitOtel {
  enableTelemetry(telemetryConfig: TelemetryConfig | Promise<TelemetryConfig>) {
    enableTelemetry(telemetryConfig);
  }

  async shutdown(): Promise<void> {
    await cleanUpTracing();
  }

  async flushTracing(): Promise<void> {
    await flushTracing;
  }

  async flushMetrics(): Promise<void> {
    await maybeFlushMetrics();
  }
}

/**
 * Enables tracing and metrics open telemetry configuration.
 */
async function enableTelemetry(
  telemetryConfig: TelemetryConfig | Promise<TelemetryConfig>
) {
  if (getEnvVar('GENKIT_TELEMETRY_SERVER')) {
    setTelemetryServerUrl(getEnvVar('GENKIT_TELEMETRY_SERVER')!);
  }

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

async function cleanUpTracing(): Promise<void> {
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
async function flushTracing() {
  if (nodeOtelConfig?.spanProcessors) {
    await Promise.all(nodeOtelConfig.spanProcessors.map((p) => p.forceFlush()));
  }
}
