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
import { spanMetadataAls, traceMetadataAls } from '@genkit-ai/core/tracing';
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

const variantCounter = new MetricCounter(_N('variants'), {
  description: 'Tracks unique flow variants per flow.',
  valueType: ValueType.INT,
});

const flowLatencies = new MetricHistogram(_N('latency'), {
  description: 'Latencies when calling Genkit flows.',
  valueType: ValueType.DOUBLE,
  unit: 'ms',
});

export function recordError(err: any) {
  const path = spanMetadataAls?.getStore()?.path;
  logger.logStructuredError(`Error[${path}, ${err.name}]`, {
    path: path,
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
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  };
  flowCounter.add(1, dimensions);
  flowLatencies.record(latencyMs, dimensions);

  const paths = traceMetadataAls.getStore()?.paths || new Set<string>();
  if (paths) {
    const relevantVariants = Array.from(paths).filter((path) =>
      path.includes(flowName)
    );

    logger.logStructured(`Variants[/${flowName}]`, {
      flowName: flowName,
      variants: relevantVariants,
    });

    relevantVariants.forEach((variant) =>
      variantCounter.add(1, {
        ...dimensions,
        success: 'success',
        variant,
      })
    );
  }
}

export function writeFlowFailure(
  flowName: string,
  latencyMs: number,
  err: any
) {
  const dimensions = {
    name: flowName,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
    error: err.name,
  };
  flowCounter.add(1, dimensions);
  flowLatencies.record(latencyMs, dimensions);

  const allPaths = traceMetadataAls.getStore()?.paths || new Set<string>();
  if (allPaths) {
    const failPath = spanMetadataAls?.getStore()?.path;
    const relevantVariants = Array.from(allPaths).filter(
      (path) => path.includes(flowName) && path !== failPath
    );

    logger.logStructured(`Variants[/${flowName}]`, {
      flowName: flowName,
      variants: relevantVariants,
    });

    // All variants that have succeeded need to be tracked as succeeded.
    relevantVariants.forEach((variant) =>
      variantCounter.add(1, {
        flowName: flowName,
        success: 'success',
        variant: variant,
      })
    );

    variantCounter.add(1, {
      flowName: flowName,
      success: 'failure',
      variant: failPath,
    });
  }
}

export function logRequest(flowName: string, req: express.Request) {
  logger.logStructured(`Request[/${flowName}]`, {
    flowName: flowName,
    headers: {
      ...req.headers,
      authorization: '<redacted>',
    },
    params: req.params,
    body: req.body,
    query: req.query,
    originalUrl: req.originalUrl,
    path: `/${flowName}`,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  });
}

export function logResponse(flowName: string, respCode: number, respBody: any) {
  logger.logStructured(`Response[/${flowName}]`, {
    flowName: flowName,
    path: `/${flowName}`,
    code: respCode,
    body: respBody,
    source: 'ts',
    sourceVersion: GENKIT_VERSION,
  });
}
