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
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node/build/src/types';
import {
  BatchSpanProcessor,
  SimpleSpanProcessor,
  SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import { logger } from './logging.js';
import { TelemetryConfig } from './telemetryTypes.js';
import { TraceServerExporter } from './tracing/exporter.js';
import { MultiSpanProcessor } from './tracing/multiSpanProcessor.js';
import { getCurrentEnv } from './utils.js';

export * from './tracing/exporter.js';
export * from './tracing/instrumentation.js';
export * from './tracing/processor.js';
export * from './tracing/types.js';

const processors: SpanProcessor[] = [];
let telemetrySDK: NodeSDK | null = null;
let nodeOtelConfig: Partial<NodeSDKConfiguration> | null = null;

/**
 * Enables tracing and metrics open telemetry configuration.
 */
export function enableTracingAndMetrics(telemetryConfig: TelemetryConfig) {
  if (process.env['GENKIT_TELEMETRY_SERVER']) {
    addProcessor(
      createTraceProcessor(process.env['GENKIT_TELEMETRY_SERVER'], 'batch')
    );
  }

  nodeOtelConfig = telemetryConfig.getConfig() || {};

  addProcessor(nodeOtelConfig.spanProcessor);
  nodeOtelConfig.spanProcessor = new MultiSpanProcessor(processors);
  telemetrySDK = new NodeSDK(nodeOtelConfig);
  telemetrySDK.start();
  process.on('SIGTERM', async () => await cleanUpTracing());
}

export async function cleanUpTracing(): Promise<void> {
  return new Promise((resolve) => {
    if (telemetrySDK) {
      // Metrics are not flushed as part of the shutdown operation. If metrics
      // are enabled, we need to manually flush them *before* the reader
      // receives shutdown order.
      const metricFlush = maybeFlushMetrics();

      return metricFlush.then(() => {
        return telemetrySDK!.shutdown().then(() => {
          logger.debug('OpenTelemetry SDK shut down.');
          telemetrySDK = null;
          resolve();
        });
      });
    } else {
      resolve();
    }
  });
}

/**
 * Creates a new SpanProcessor for exporting data to the telemetry server.
 */
function createTraceProcessor(
  url: string,
  processor: 'batch' | 'simple'
): SpanProcessor {
  logger.debug(`Sending telemetry to ${url}`);
  const exporter = new TraceServerExporter(url);
  return processor === 'simple' || getCurrentEnv() === 'dev'
    ? new SimpleSpanProcessor(exporter)
    : new BatchSpanProcessor(exporter);
}

/** Adds the given {SpanProcessor} to the list of processors */
function addProcessor(processor: SpanProcessor | undefined) {
  if (processor) processors.push(processor);
}

/** Flush metrics if present. */
function maybeFlushMetrics(): Promise<void> {
  if (nodeOtelConfig?.metricReader) {
    return nodeOtelConfig.metricReader.forceFlush();
  }
  return Promise.resolve();
}

/**
 * Flushes all configured span processors
 */
export async function flushTracing() {
  await Promise.all(processors.map((p) => p.forceFlush()));
}
