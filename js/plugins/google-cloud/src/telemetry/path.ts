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
import { hrTimeDuration, hrTimeToMilliseconds } from '@opentelemetry/core';
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import { GENKIT_VERSION } from 'genkit';
import { logger } from 'genkit/logging';
import { PathMetadata, toDisplayPath } from 'genkit/tracing';
import {
  MetricCounter,
  MetricHistogram,
  Telemetry,
  internalMetricNamespaceWrap,
} from '../metrics.js';
import {
  createCommonLogAttributes,
  extractErrorMessage,
  extractErrorName,
  extractErrorStack,
  truncatePath,
} from '../utils.js';

class PathsTelemetry implements Telemetry {
  /**
   * Wraps the declared metrics in a Genkit-specific, internal namespace.
   */
  private _N = internalMetricNamespaceWrap.bind(null, 'feature');

  private pathCounter = new MetricCounter(this._N('path/requests'), {
    description: 'Tracks unique flow paths per flow.',
    valueType: ValueType.INT,
  });

  private pathLatencies = new MetricHistogram(this._N('path/latency'), {
    description: 'Latencies per flow path.',
    ValueType: ValueType.DOUBLE,
    unit: 'ms',
  });

  tick(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    logInputAndOutput: boolean,
    projectId?: string
  ): void {
    const attributes = span.attributes;
    const name = attributes['genkit:name'] as string;
    const path = attributes['genkit:path'] as string;
    const sessionId = attributes['genkit:sessionId'] as string;
    const threadName = attributes['genkit:threadName'] as string;

    const latencyMs = hrTimeToMilliseconds(
      hrTimeDuration(span.startTime, span.endTime)
    );
    const state = attributes['genkit:state'] as string;

    if (state === 'success') {
      this.writePathSuccess(
        span,
        paths!,
        name,
        path,
        latencyMs,
        projectId,
        sessionId,
        threadName
      );
      return;
    }

    if (state === 'error') {
      const errorName = extractErrorName(span.events) || '<unknown>';
      const errorMessage = extractErrorMessage(span.events) || '<unknown>';
      const errorStack = extractErrorStack(span.events) || '';

      this.writePathFailure(
        span,
        paths!,
        name,
        path,
        latencyMs,
        errorName,
        projectId,
        sessionId,
        threadName
      );
      this.recordError(
        span,
        path,
        errorName,
        errorMessage,
        errorStack,
        projectId,
        sessionId,
        threadName
      );
      return;
    }

    logger.warn(`Unknown state; ${state}`);
  }

  private recordError(
    span: ReadableSpan,
    path: string,
    errorName: string,
    errorMessage: string,
    errorStack: string,
    projectId?: string,
    sessionId?: string,
    threadName?: string
  ) {
    const displayPath = truncatePath(toDisplayPath(path));
    logger.logStructuredError(`Error[${displayPath}, ${errorName}]`, {
      ...createCommonLogAttributes(span, projectId),
      path: displayPath,
      qualifiedPath: path,
      name: errorName,
      message: errorMessage,
      stack: errorStack,
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
      sessionId,
      threadName,
    });
  }

  private writePathSuccess(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    featureName: string,
    path: string,
    latencyMs: number,
    projectId?: string,
    sessionId?: string,
    threadName?: string
  ) {
    this.writePathMetrics(
      span,
      path,
      paths,
      featureName,
      latencyMs,
      undefined,
      projectId,
      sessionId,
      threadName
    );
  }

  private writePathFailure(
    span: ReadableSpan,
    paths: Set<PathMetadata>,
    featureName: string,
    path: string,
    latencyMs: number,
    errorName: string,
    projectId?: string,
    sessionId?: string,
    threadName?: string
  ) {
    this.writePathMetrics(
      span,
      path,
      paths,
      featureName,
      latencyMs,
      errorName,
      projectId,
      sessionId,
      threadName
    );
  }

  /** Writes all path-level metrics stored in the current flow execution. */
  private writePathMetrics(
    span: ReadableSpan,
    rootPath: string,
    paths: Set<PathMetadata>,
    featureName: string,
    latencyMs: number,
    err?: string,
    projectId?: string,
    sessionId?: string,
    threadName?: string
  ) {
    const flowPaths = Array.from(paths).filter((meta) =>
      meta.path.includes(featureName)
    );

    if (flowPaths) {
      logger.logStructured(`Paths[${featureName}]`, {
        ...createCommonLogAttributes(span, projectId),
        flowName: featureName,
        sessionId,
        threadName,
        paths: flowPaths.map((p) => truncatePath(toDisplayPath(p.path))),
      });

      flowPaths.forEach((p) => this.writePathMetric(featureName, p));
      // If we're writing a failure, but none of the stored paths have failed,
      // this means the root flow threw the error.
      if (err && !flowPaths.some((p) => p.status === 'failure')) {
        this.writePathMetric(featureName, {
          status: 'failure',
          path: rootPath,
          error: err,
          latency: latencyMs,
        });
      }
    }
  }

  /** Writes metrics for a single PathMetadata */
  private writePathMetric(featureName: string, meta: PathMetadata) {
    const pathDimensions = {
      featureName: featureName,
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

const pathsTelemetry = new PathsTelemetry();
export { pathsTelemetry };
