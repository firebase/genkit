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
  SpanProcessor,
} from '@opentelemetry/sdk-trace-base';
import { getCurrentEnv } from './config';
import { TelemetryConfig } from './telemetryTypes';
import { TraceStore } from './tracing';
import { TraceStoreExporter } from './tracing/exporter';
import { MultiSpanProcessor } from './tracing/multiSpanProcessor';

export * from './tracing/exporter.js';
export * from './tracing/firestoreTraceStore.js';
export * from './tracing/instrumentation.js';
export * from './tracing/localFileTraceStore.js';
export * from './tracing/processor.js';
export * from './tracing/types.js';

const processors: SpanProcessor[] = [];

/**
 * Enables trace spans to be written to the trace store.
 */
export function enableTracingAndMetrics(
  telemetryConfig: TelemetryConfig,
  traceStore?: TraceStore,
  traceStoreOptions: {
    processor?: 'batch' | 'simple';
  } = {}
) {
  if (traceStore) {
    addProcessor(
      createTraceStoreProcessor(
        traceStore,
        traceStoreOptions.processor || 'batch'
      )
    );
  }

  const nodeOtelConfig = telemetryConfig.getConfig() || {};

  addProcessor(nodeOtelConfig.spanProcessor);
  nodeOtelConfig.spanProcessor = new MultiSpanProcessor(processors);
  const sdk = new NodeSDK(nodeOtelConfig);

  sdk.start();
}

/**
 * Creates a new SpanProcessor for exporting data to the configured TraceStore.
 *
 * Returns `undefined` if no trace store implementation is configured.
 */
function createTraceStoreProcessor(
  traceStore: TraceStore,
  processor: 'batch' | 'simple'
): SpanProcessor {
  const exporter = new TraceStoreExporter(traceStore);
  return processor === 'simple' || getCurrentEnv() === 'dev'
    ? new SimpleSpanProcessor(exporter)
    : new BatchSpanProcessor(exporter);
}

/** Adds the given {SpanProcessor} to the list of processors */
function addProcessor(processor: SpanProcessor | undefined) {
  if (processor) processors.push(processor);
}

/**
 * Flushes all configured span processors
 */
export async function flushTracing() {
  await Promise.all(processors.map((p) => p.forceFlush()));
}
