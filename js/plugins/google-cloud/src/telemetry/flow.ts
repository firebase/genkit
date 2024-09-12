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
import { PathMetadata, toDisplayPath } from '@genkit-ai/core/tracing';
import { ValueType } from '@opentelemetry/api';
import { hrTimeDuration, hrTimeToMilliseconds } from '@opentelemetry/core';
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import {
  MetricCounter,
  MetricHistogram,
  Telemetry,
  internalMetricNamespaceWrap,
} from '../metrics';
import {
  createCommonLogAttributes,
  extractErrorMessage,
  extractErrorName,
  extractErrorStack,
} from '../utils';

class FlowsTelemetry implements Telemetry {
  /**
   * Wraps the declared metrics in a Genkit-specific, internal namespace.
   */
  private _N = internalMetricNamespaceWrap.bind(null, 'flow');

  private flowCounter = new MetricCounter(this._N('requests'), {
    description: 'Counts calls to genkit flows.',
    valueType: ValueType.INT,
  });

  private pathCounter = new MetricCounter(this._N('path/requests'), {
    description: 'Tracks unique flow paths per flow.',
    valueType: ValueType.INT,
  });

  private pathLatencies = new MetricHistogram(this._N('path/latency'), {
    description: 'Latencies per flow path.',
    ValueType: ValueType.DOUBLE,
    unit: 'ms',
  });

  private flowLatencies = new MetricHistogram(this._N('latency'), {
    description: 'Latencies when calling Genkit flows.',
    valueType: ValueType.DOUBLE,
    unit: 'ms',
  });

  tick(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    logIO: boolean,
    projectId?: string
  ): void {
    const attributes = span.attributes;
    const name = attributes['genkit:name'] as string;
    const path = attributes['genkit:path'] as string;
    const latencyMs = hrTimeToMilliseconds(
      hrTimeDuration(span.startTime, span.endTime)
    );
    const isRoot = (attributes['genkit:isRoot'] as boolean) || false;
    const state = attributes['genkit:state'] as string;

    const input = attributes['genkit:input'] as string;
    const output = attributes['genkit:output'] as string;

    if (input && logIO) {
      this.recordIO(span, 'Input', name, path, input, projectId);
    }

    if (output && logIO) {
      this.recordIO(span, 'Output', name, path, output, projectId);
    }

    if (state === 'success') {
      this.writeFlowSuccess(
        span,
        paths!,
        name,
        path,
        latencyMs,
        isRoot,
        projectId
      );
      return;
    }

    if (state === 'error') {
      const errorName = extractErrorName(span.events) || '<unknown>';
      const errorMessage = extractErrorMessage(span.events) || '<unknown>';
      const errorStack = extractErrorStack(span.events) || '';

      this.writeFlowFailure(
        span,
        paths!,
        name,
        path,
        latencyMs,
        errorName,
        isRoot,
        projectId
      );
      this.recordError(
        span,
        path,
        errorName,
        errorMessage,
        errorStack,
        projectId
      );
      return;
    }

    logger.warn(`Unknown flow state; ${state}`);
  }

  private recordIO(
    span: ReadableSpan,
    tag: string,
    flowName: string,
    qualifiedPath: string,
    input: string,
    projectId?: string
  ) {
    const path = toDisplayPath(qualifiedPath);
    const sharedMetadata = {
      ...createCommonLogAttributes(span, projectId),
      path,
      qualifiedPath,
      flowName,
    };
    logger.logStructured(`${tag}[${path}, ${flowName}]`, {
      ...sharedMetadata,
      content: input,
    });
  }

  private recordError(
    span: ReadableSpan,
    path: string,
    errorName: string,
    errorMessage: string,
    errorStack: string,
    projectId?: string
  ) {
    const displayPath = toDisplayPath(path);
    logger.logStructuredError(`Error[${displayPath}, ${errorName}]`, {
      ...createCommonLogAttributes(span, projectId),
      path: displayPath,
      qualifiedPath: path,
      name: errorName,
      message: errorMessage,
      stack: errorStack,
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
    });
  }

  private writeFlowSuccess(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    flowName: string,
    path: string,
    latencyMs: number,
    isRoot: boolean,
    projectId?: string
  ) {
    const dimensions = {
      name: flowName,
      status: 'success',
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
    };
    this.flowCounter.add(1, dimensions);
    this.flowLatencies.record(latencyMs, dimensions);

    if (isRoot) {
      this.writePathMetrics(
        span,
        path,
        paths,
        flowName,
        latencyMs,
        undefined,
        projectId
      );
    }
  }

  private writeFlowFailure(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    flowName: string,
    path: string,
    latencyMs: number,
    errorName: string,
    isRoot: boolean,
    projectId?: string
  ) {
    const dimensions = {
      name: flowName,
      status: 'failure',
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
      error: errorName,
    };
    this.flowCounter.add(1, dimensions);
    this.flowLatencies.record(latencyMs, dimensions);

    if (isRoot) {
      this.writePathMetrics(
        span,
        path,
        paths,
        flowName,
        latencyMs,
        errorName,
        projectId
      );
    }
  }

  /** Writes all path-level metrics stored in the current flow execution. */
  private writePathMetrics(
    span: ReadableSpan,
    rootPath: string,
    paths: Set<PathMetadata>,
    flowName: string,
    latencyMs: number,
    err?: string,
    projectId?: string
  ) {
    const flowPaths = Array.from(paths).filter((meta) =>
      meta.path.includes(flowName)
    );

    if (flowPaths) {
      logger.logStructured(`Paths[${flowName}]`, {
        ...createCommonLogAttributes(span, projectId),
        flowName: flowName,
        paths: flowPaths.map((p) => toDisplayPath(p.path)),
      });

      flowPaths.forEach((p) => this.writePathMetric(flowName, p));
      // If we're writing a failure, but none of the stored paths have failed,
      // this means the root flow threw the error.
      if (err && !flowPaths.some((p) => p.status === 'failure')) {
        this.writePathMetric(flowName, {
          status: 'failure',
          path: rootPath,
          error: err,
          latency: latencyMs,
        });
      }
    }
  }

  /** Writes metrics for a single PathMetadata */
  private writePathMetric(flowName: string, meta: PathMetadata) {
    const pathDimensions = {
      flowName: flowName,
      status: meta.status,
      error: meta.error,
      path: meta.path,
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
    };
    this.pathCounter.add(1, pathDimensions);
    this.pathLatencies.record(meta.latency, pathDimensions);
  }
}

const flowsTelemetry = new FlowsTelemetry();
export { flowsTelemetry };
