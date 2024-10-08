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
import { GENKIT_VERSION, GenkitError } from 'genkit';
import { logger } from 'genkit/logging';
import { PathMetadata } from 'genkit/tracing';
import {
  MetricCounter,
  MetricHistogram,
  Telemetry,
  internalMetricNamespaceWrap,
} from '../metrics';
import { extractErrorName } from '../utils';

class FeaturesTelemetry implements Telemetry {
  /**
   * Wraps the declared metrics in a Genkit-specific, internal namespace.
   */
  private _N = internalMetricNamespaceWrap.bind(null, 'feature');

  private featureCounter = new MetricCounter(this._N('requests'), {
    description: 'Counts calls to genkit features.',
    valueType: ValueType.INT,
  });

  private featureLatencies = new MetricHistogram(this._N('latency'), {
    description: 'Latencies when calling Genkit features.',
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
    const latencyMs = hrTimeToMilliseconds(
      hrTimeDuration(span.startTime, span.endTime)
    );
    const isRoot = attributes['genkit:isRoot'] as boolean;
    if (!isRoot) {
      throw new GenkitError({
        status: 'FAILED_PRECONDITION',
        message: 'FeatureTelemetry tick called with non-root span.',
      });
    }
    const state = attributes['genkit:state'] as string;

    if (state === 'success') {
      this.writeFeatureSuccess(name, latencyMs);
      return;
    }

    if (state === 'error') {
      const errorName = extractErrorName(span.events) || '<unknown>';

      this.writeFeatureFailure(name, latencyMs, errorName);
      return;
    }

    logger.warn(`Unknown state; ${state}`);
  }

  private writeFeatureSuccess(featureName: string, latencyMs: number) {
    const dimensions = {
      name: featureName,
      status: 'success',
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
    };
    this.featureCounter.add(1, dimensions);
    this.featureLatencies.record(latencyMs, dimensions);
  }

  private writeFeatureFailure(
    featureName: string,
    latencyMs: number,
    errorName: string
  ) {
    const dimensions = {
      name: featureName,
      status: 'failure',
      source: 'ts',
      sourceVersion: GENKIT_VERSION,
      error: errorName,
    };
    this.featureCounter.add(1, dimensions);
    this.featureLatencies.record(latencyMs, dimensions);
  }
}

const featuresTelemetry = new FeaturesTelemetry();
export { featuresTelemetry };
