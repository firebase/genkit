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

import {
  MetricCounter,
  MetricHistogram,
  internalMetricNamespaceWrap,
} from './metrics';
import { ValueType } from '@opentelemetry/api';

/**
 * Wraps the declared metrics in a Genkit-specific, internal namespace.
 */
const _N = internalMetricNamespaceWrap.bind(null, 'action');

const actionCounter = new MetricCounter(_N('requests'), {
  description: 'Counts calls to genkit actions.',
  valueType: ValueType.INT,
});

const actionLatencies = new MetricHistogram(_N('action_latency'), {
  description: 'Latencies when calling Genkit actions.',
  valueType: ValueType.INT,
  unit: 'ms',
});

export function writeActionSuccess(actionName: string, latencyMs: number) {
  const dimensions = {
    actionName: actionName,
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
    actionName: actionName,
    errorCode: err?.code,
    errorMessage: err?.message,
  };
  actionCounter.add(1, dimensions);
  actionLatencies.record(latencyMs, dimensions);
}
