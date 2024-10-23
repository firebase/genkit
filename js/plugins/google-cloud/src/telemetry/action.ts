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
import { PathMetadata } from 'genkit/tracing';
import {
  MetricCounter,
  MetricHistogram,
  Telemetry,
  internalMetricNamespaceWrap,
} from '../metrics.js';
import { extractErrorName, extractOuterFeatureNameFromPath } from '../utils';

class ActionTelemetry implements Telemetry {
  /**
   * Wraps the declared metrics in a Genkit-specific, internal namespace.
   */
  private _N = internalMetricNamespaceWrap.bind(null, 'action');

  private actionCounter = new MetricCounter(this._N('requests'), {
    description: 'Counts calls to genkit actions.',
    valueType: ValueType.INT,
  });

  private actionLatencies = new MetricHistogram(this._N('latency'), {
    description: 'Latencies when calling Genkit actions.',
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

    const actionName = (attributes['genkit:name'] as string) || '<unknown>';
    const path = (attributes['genkit:path'] as string) || '<unknown>';
    let featureName = extractOuterFeatureNameFromPath(path);
    if (!featureName || featureName === '<unknown>') {
      featureName = actionName;
    }
    const state = attributes['genkit:state'] || 'success';
    const latencyMs = hrTimeToMilliseconds(
      hrTimeDuration(span.startTime, span.endTime)
    );
    const errorName = extractErrorName(span.events);

    if (state === 'success') {
      this.writeSuccess(actionName, featureName, path, latencyMs);
    } else if (state === 'error') {
      this.writeFailure(actionName, featureName, path, latencyMs, errorName);
    } else {
      logger.warn(`Unknown action state; ${state}`);
    }
  }

  private writeSuccess(
    actionName: string,
    featureName: string,
    path: string,
    latencyMs: number
  ) {
    const dimensions = {
      name: actionName,
      featureName,
      path,
      status: 'success',
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
    };
    this.actionCounter.add(1, dimensions);
    this.actionLatencies.record(latencyMs, dimensions);
  }

  private writeFailure(
    actionName: string,
    featureName: string,
    path: string,
    latencyMs: number,
    errorName?: string
  ) {
    const dimensions = {
      name: actionName,
      featureName,
      path,
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
      status: 'failure',
      error: errorName,
    };
    this.actionCounter.add(1, dimensions);
    this.actionLatencies.record(latencyMs, dimensions);
  }
}

const actionTelemetry = new ActionTelemetry();
export { actionTelemetry };
