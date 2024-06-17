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

import { ValueType } from '@opentelemetry/api';
import { GENKIT_VERSION } from './index.js';
import {
  internalMetricNamespaceWrap,
  MetricCounter,
  MetricHistogram,
} from './metrics.js';
import {
  spanMetadataAls,
  traceMetadataAls,
} from './tracing/instrumentation.js';

/**
 * Wraps the declared metrics in a Genkit-specific, internal namespace.
 */
const _N = internalMetricNamespaceWrap.bind(null, 'action');

const actionCounter = new MetricCounter(_N('requests'), {
  description: 'Counts calls to genkit actions.',
  valueType: ValueType.INT,
});

const actionLatencies = new MetricHistogram(_N('latency'), {
  description: 'Latencies when calling Genkit actions.',
  valueType: ValueType.DOUBLE,
  unit: 'ms',
});

export function writeActionSuccess(actionName: string, latencyMs: number) {
  const dimensions = {
    name: actionName,
    flowName: traceMetadataAls?.getStore()?.flowName,
    path: spanMetadataAls?.getStore()?.path,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  };
  actionCounter.add(1, dimensions);
  actionLatencies.record(latencyMs, dimensions);
}

export function writeActionFailure(
  actionName: string,
  latencyMs: number,
  err: any
) {
  const dimensions = {
    name: actionName,
    flowName: traceMetadataAls?.getStore()?.flowName,
    path: spanMetadataAls?.getStore()?.path,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
    error: err?.name,
  };
  actionCounter.add(1, dimensions);
  actionLatencies.record(latencyMs, dimensions);
}
