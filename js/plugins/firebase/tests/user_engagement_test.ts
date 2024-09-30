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
  GcpOpenTelemetry,
  __forceFlushSpansForTesting,
  __getMetricExporterForTesting,
  __getSpanExporterForTesting,
  googleCloud,
} from '@genkit-ai/google-cloud';
import {
  DataPoint,
  Histogram,
  HistogramMetricData,
  ScopeMetrics,
  SumMetricData,
} from '@opentelemetry/sdk-metrics';
import { after, before, beforeEach, describe, it } from 'node:test';
import {collectUserEngagement, FirebaseUserFeedbackEnum, FirebaseUserEngagementSchema} from '../src/user_engagement';
import {Genkit, genkit} from 'genkit';
import assert from 'node:assert';

describe('User Engagement', () => {
  let ai: Genkit;

  before(async () => {
    process.env.GENKIT_ENV = 'dev';
    ai = genkit({
      // Force GCP Plugin to use in-memory metrics exporter
      plugins: [
        googleCloud({
          projectId: 'test',
          telemetryConfig: {
            forceDevExport: false,
            metricExportIntervalMillis: 100,
            metricExportTimeoutMillis: 100,
          },
        }),
      ],
      enableTracingAndMetrics: true,
      telemetry: {
        logger: '',
        instrumentation: 'googleCloud',
      },
    });
    // Wait for the telemetry plugin to be initialized
    await ai.getTelemetryConfig();
  });
  beforeEach(async () => {
    __getMetricExporterForTesting().reset();
    __getSpanExporterForTesting().reset();
  });
  after(async () => {
    await ai.stopServers();
  });

  it('ticks user engagement metrics', async () => {
    collectUserEngagement(FirebaseUserEngagementSchema.parse({
      name: "flow_name",
      traceId: "trace1",
      spanId: "span1",
      feedback: {
        value: FirebaseUserFeedbackEnum.POSITIVE,
        text: "great feature!"
      }
    }));
  });

  // TODO: refactor into helper class??
  /** Finds a counter metric with the given name in the in memory exporter */
  async function getCounterMetric(
    metricName: string
  ): Promise<DataPoint<number>> {
    const counter = await getCounterDataPoints(metricName).then((points) =>
      points.at(-1)
    );
    if (counter === undefined) {
      assert.fail(`Counter not found`);
    } else {
      return counter;
    }
  }

  /** Finds all datapoints for a counter metric with the given name in the in memory exporter */
  async function getCounterDataPoints(
    metricName: string
  ): Promise<Array<DataPoint<number>>> {
    const genkitMetrics = await getGenkitMetrics();
    if (genkitMetrics) {
      const counterMetric: SumMetricData = genkitMetrics.metrics.find(
        (e) =>
          e.descriptor.name === metricName && e.descriptor.type === 'COUNTER'
      ) as SumMetricData;
      if (counterMetric) {
        return counterMetric.dataPoints;
      }
      assert.fail(
        `No counter metric named ${metricName} was found. Only found: ${genkitMetrics.metrics.map((e) => e.descriptor.name)}`
      );
    } else {
      assert.fail(`No genkit metrics found.`);
    }
  }

  /** Polls the in memory metric exporter until the genkit scope is found. */
  async function getGenkitMetrics(
    name: string = 'genkit',
    maxAttempts: number = 100
  ): Promise<ScopeMetrics | undefined> {
    var attempts = 0;
    while (attempts++ < maxAttempts) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      const found = __getMetricExporterForTesting()
        .getMetrics()
        .find((e) => e.scopeMetrics.map((sm) => sm.scope.name).includes(name));
      if (found) {
        return found.scopeMetrics.find((e) => e.scope.name === name);
      }
    }
    assert.fail(`Waiting for metric ${name} but it has not been written.`);
  }
});
