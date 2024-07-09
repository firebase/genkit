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

import { GENKIT_VERSION } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import {
  internalMetricNamespaceWrap,
  MetricCounter,
  MetricHistogram,
} from '@genkit-ai/core/metrics';
import {
  PathMetadata,
  spanMetadataAls,
  toDisplayPath,
  traceMetadataAls,
} from '@genkit-ai/core/tracing';
import { ValueType } from '@opentelemetry/api';
import express from 'express';

/**
 * Wraps the declared metrics in a Genkit-specific, internal namespace.
 */
const _N = internalMetricNamespaceWrap.bind(null, 'flow');

const flowCounter = new MetricCounter(_N('requests'), {
  description: 'Counts calls to genkit flows.',
  valueType: ValueType.INT,
});

const pathCounter = new MetricCounter(_N('path/requests'), {
  description: 'Tracks unique flow paths per flow.',
  valueType: ValueType.INT,
});

const pathLatencies = new MetricHistogram(_N('path/latency'), {
  description: 'Latencies per flow path.',
  ValueType: ValueType.DOUBLE,
  unit: 'ms',
});

const flowLatencies = new MetricHistogram(_N('latency'), {
  description: 'Latencies when calling Genkit flows.',
  valueType: ValueType.DOUBLE,
  unit: 'ms',
});

export function recordError(err: any) {
  const qualifiedPath = spanMetadataAls?.getStore()?.path || '';
  const path = toDisplayPath(qualifiedPath);
  logger.logStructuredError(`Error[${path}, ${err.name}]`, {
    path,
    qualifiedPath,
    name: err.name,
    message: err.message,
    stack: err.stack,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  });
}

export function writeFlowSuccess(flowName: string, latencyMs: number) {
  const dimensions = {
    name: flowName,
    status: 'success',
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  };
  flowCounter.add(1, dimensions);
  flowLatencies.record(latencyMs, dimensions);

  writePathMetrics(flowName, latencyMs);
}

export function writeFlowFailure(
  flowName: string,
  latencyMs: number,
  err: any
) {
  const dimensions = {
    name: flowName,
    status: 'failure',
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
    error: err.name,
  };
  flowCounter.add(1, dimensions);
  flowLatencies.record(latencyMs, dimensions);

  writePathMetrics(flowName, latencyMs, err);
}

export function logRequest(flowName: string, req: express.Request) {
  const qualifiedPath = spanMetadataAls?.getStore()?.path || '';
  const path = toDisplayPath(qualifiedPath);
  logger.logStructured(`Request[${flowName}]`, {
    flowName: flowName,
    headers: {
      ...req.headers,
      authorization: '<redacted>',
    },
    params: req.params,
    body: req.body,
    query: req.query,
    originalUrl: req.originalUrl,
    path,
    qualifiedPath,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  });
}

export function logResponse(flowName: string, respCode: number, respBody: any) {
  const qualifiedPath = spanMetadataAls?.getStore()?.path || '';
  const path = toDisplayPath(qualifiedPath);
  logger.logStructured(`Response[${flowName}]`, {
    flowName: flowName,
    path,
    qualifiedPath,
    code: respCode,
    body: respBody,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  });
}

/** Writes all path-level metrics stored in the current flow execution. */
function writePathMetrics(flowName: string, latencyMs: number, err?: any) {
  const paths = traceMetadataAls.getStore()?.paths || new Set<PathMetadata>();
  const flowPaths = Array.from(paths).filter((meta) =>
    meta.path.includes(flowName)
  );
  if (flowPaths) {
    logger.logStructured(`Paths[${flowName}]`, {
      flowName: flowName,
      paths: flowPaths.map((p) => toDisplayPath(p.path)),
    });

    flowPaths.forEach((p) => writePathMetric(flowName, p));
    // If we're writing a failure, but none of the stored paths have failed,
    // this means the root flow threw the error.
    if (err && !flowPaths.some((p) => p.status === 'failure')) {
      writePathMetric(flowName, {
        status: 'failure',
        path: spanMetadataAls?.getStore()?.path || '',
        error: err,
        latency: latencyMs,
      });
    }
  }
}

/** Writes metrics for a single PathMetadata */
function writePathMetric(flowName: string, meta: PathMetadata) {
  const pathDimensions = {
    flowName: flowName,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  };
  pathCounter.add(1, {
    ...pathDimensions,
    status: meta.status,
    error: meta.error,
    path: meta.path,
  });

  pathLatencies.record(meta.latency, {
    ...pathDimensions,
    status: meta.status,
    error: meta.error,
    path: meta.path,
  });
}
