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
  internalMetricNamespaceWrap,
  MetricCounter,
  MetricHistogram,
} from '@genkit-ai/common/metrics';
import { ValueType } from '@opentelemetry/api';

/**
 * Wraps the declared metrics in a Genkit-specific, internal namespace.
 */
const _N = internalMetricNamespaceWrap.bind(null, 'flow');

const flowCounter = new MetricCounter(_N('requests'), {
  description: 'Counts calls to genkit flows.',
  valueType: ValueType.INT,
});

const flowLatencies = new MetricHistogram(_N('flow_latency'), {
  description: 'Latencies when calling Genkit flows.',
  valueType: ValueType.INT,
  unit: 'ms',
});

export function writeFlowSuccess(flowName: string, latencyMs: number) {
  const dimensions = {
    flowName: flowName,
  };
  flowCounter.add(1, dimensions);
  flowLatencies.record(latencyMs, dimensions);
}

export function writeFlowFailure(
  flowName: string,
  latencyMs: number,
  err: any
) {
  const dimensions = {
    flowName: flowName,
    errorCode: err?.code,
    errorMessage: err?.message,
  };
  flowCounter.add(1, dimensions);
  flowLatencies.record(latencyMs, dimensions);
}
