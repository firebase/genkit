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

import { generate } from '@genkit-ai/ai';
import { defineModel } from '@genkit-ai/ai/model';
import {
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateStore,
  configureGenkit,
  defineAction,
} from '@genkit-ai/core';
import { registerFlowStateStore } from '@genkit-ai/core/registry';
import { defineFlow, runAction, runFlow } from '@genkit-ai/flow';
import {
  GcpOpenTelemetry,
  __getMetricExporterForTesting,
  googleCloud,
} from '@genkit-ai/google-cloud';
import {
  Counter,
  DataPoint,
  Histogram,
  ScopeMetrics,
  SumMetricData,
} from '@opentelemetry/sdk-metrics';
import assert from 'node:assert';
import { before, beforeEach, describe, it } from 'node:test';
import { z } from 'zod';

describe('GoogleCloudMetrics', () => {
  before(async () => {
    process.env.GENKIT_ENV = 'dev';
    const config = configureGenkit({
      // Force GCP Plugin to use in-memory metrics exporter
      plugins: [
        googleCloud({
          forceDevExport: false,
          telemetryConfig: {
            metricExportIntervalMillis: 100,
            metricExportTimeoutMillis: 100,
          },
        }),
      ],
      enableTracingAndMetrics: true,
      telemetry: {
        instrumentation: 'googleCloud',
      },
    });
    registerFlowStateStore('dev', async () => new NoOpFlowStateStore());
    // Wait for the telemetry plugin to be initialized
    await config.getTelemetryConfig();
  });
  beforeEach(async () => {
    __getMetricExporterForTesting().reset();
  });

  it('writes flow metrics', async () => {
    const testFlow = createFlow('testFlow');

    await runFlow(testFlow);
    await runFlow(testFlow);

    const requestCounter = await getCounterMetric('genkit/flow/requests');
    const latencyHistogram = await getHistogramMetric('genkit/flow/latency');
    assert.equal(requestCounter.value, 2);
    assert.equal(requestCounter.attributes.name, 'testFlow');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.ok(requestCounter.attributes.sourceVersion);
    assert.equal(latencyHistogram.value.count, 2);
    assert.equal(latencyHistogram.attributes.name, 'testFlow');
    assert.equal(latencyHistogram.attributes.source, 'ts');
    assert.ok(latencyHistogram.attributes.sourceVersion);
  });

  it('writes flow failure metrics', async () => {
    const testFlow = createFlow('testFlow', async () => {
      const nothing = null;
      nothing.something;
    });

    assert.rejects(async () => {
      await runFlow(testFlow);
    });

    const requestCounter = await getCounterMetric('genkit/flow/requests');
    assert.equal(requestCounter.value, 1);
    assert.equal(requestCounter.attributes.name, 'testFlow');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.error, 'TypeError');
  });

  it('writes action metrics', async () => {
    const testAction = createAction('testAction');
    const testFlow = createFlow('testFlowWithActions', async () => {
      await Promise.all([
        runAction(testAction),
        runAction(testAction),
        runAction(testAction),
      ]);
    });

    await runFlow(testFlow);
    await runFlow(testFlow);

    const requestCounter = await getCounterMetric('genkit/action/requests');
    const latencyHistogram = await getHistogramMetric('genkit/action/latency');
    assert.equal(requestCounter.value, 6);
    assert.equal(requestCounter.attributes.name, 'testAction');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.ok(requestCounter.attributes.sourceVersion);
    assert.equal(latencyHistogram.value.count, 6);
    assert.equal(latencyHistogram.attributes.name, 'testAction');
    assert.equal(latencyHistogram.attributes.source, 'ts');
    assert.ok(latencyHistogram.attributes.sourceVersion);
  });

  it('truncates metric dimensions', async () => {
    const testFlow = createFlow('anExtremelyLongFlowNameThatIsTooBig');

    await runFlow(testFlow);

    const requestCounter = await getCounterMetric('genkit/flow/requests');
    const latencyHistogram = await getHistogramMetric('genkit/flow/latency');
    assert.equal(requestCounter.attributes.name, 'anExtremelyLongFlowNameThatIsToo');
    assert.equal(latencyHistogram.attributes.name, 'anExtremelyLongFlowNameThatIsToo');
  });

  it('writes action failure metrics', async () => {
    const testAction = createAction('testActionWithFailure', async () => {
      const nothing = null;
      nothing.something;
    });
    const testFlow = createFlow('testFlowWithFailingActions', async () => {
      await runAction(testAction);
    });

    assert.rejects(async () => {
      await runFlow(testFlow);
    });

    const requestCounter = await getCounterMetric('genkit/action/requests');
    assert.equal(requestCounter.value, 1);
    assert.equal(requestCounter.attributes.name, 'testActionWithFailure');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.error, 'TypeError');
  });

  it('writes generate metrics', async () => {
    const testModel = createModel('testModel', async () => {
      return {
        candidates: [
          {
            index: 0,
            finishReason: 'stop',
            message: {
              role: 'user',
              content: [
                {
                  text: 'response',
                },
              ],
            },
          },
        ],
        usage: {
          inputTokens: 10,
          outputTokens: 14,
          inputCharacters: 8,
          outputCharacters: 16,
          inputImages: 1,
          outputImages: 3,
        },
      };
    });

    const response = await generate({
      model: testModel,
      prompt: 'test prompt',
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });

    const requestCounter = await getCounterMetric(
      'genkit/ai/generate/requests'
    );
    const inputTokenCounter = await getCounterMetric(
      'genkit/ai/generate/input/tokens'
    );
    const outputTokenCounter = await getCounterMetric(
      'genkit/ai/generate/output/tokens'
    );
    const inputCharacterCounter = await getCounterMetric(
      'genkit/ai/generate/input/characters'
    );
    const outputCharacterCounter = await getCounterMetric(
      'genkit/ai/generate/output/characters'
    );
    const inputImageCounter = await getCounterMetric(
      'genkit/ai/generate/input/images'
    );
    const outputImageCounter = await getCounterMetric(
      'genkit/ai/generate/output/images'
    );
    const latencyHistogram = await getHistogramMetric(
      'genkit/ai/generate/latency'
    );
    assert.equal(requestCounter.value, 1);
    assert.equal(requestCounter.attributes.maxOutputTokens, 7);
    assert.equal(inputTokenCounter.value, 10);
    assert.equal(outputTokenCounter.value, 14);
    assert.equal(inputCharacterCounter.value, 8);
    assert.equal(outputCharacterCounter.value, 16);
    assert.equal(inputImageCounter.value, 1);
    assert.equal(outputImageCounter.value, 3);
    assert.equal(latencyHistogram.value.count, 1);
    for (metric of [
      requestCounter,
      inputTokenCounter,
      outputTokenCounter,
      inputCharacterCounter,
      outputCharacterCounter,
      inputImageCounter,
      outputImageCounter,
      latencyHistogram,
    ]) {
      assert.equal(metric.attributes.modelName, 'testModel');
      assert.equal(metric.attributes.temperature, 1.0);
      assert.equal(metric.attributes.topK, 3);
      assert.equal(metric.attributes.topP, 5);
      assert.equal(metric.attributes.source, 'ts');
      assert.ok(metric.attributes.sourceVersion);
    }
  });

  it('writes generate failure metrics', async () => {
    const testModel = createModel('failingTestModel', async () => {
      const nothing = null;
      nothing.something;
    });

    assert.rejects(async () => {
      return await generate({
        model: testModel,
        prompt: 'test prompt',
        config: {
          temperature: 1.0,
          topK: 3,
          topP: 5,
          maxOutputTokens: 7,
        },
      });
    });

    const requestCounter = await getCounterMetric(
      'genkit/ai/generate/requests'
    );
    assert.equal(requestCounter.value, 1);
    assert.equal(requestCounter.attributes.modelName, 'failingTestModel');
    assert.equal(requestCounter.attributes.temperature, 1.0);
    assert.equal(requestCounter.attributes.topK, 3);
    assert.equal(requestCounter.attributes.topP, 5);
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.error, 'TypeError');
    assert.ok(requestCounter.attributes.sourceVersion);
  });

  describe('Configuration', () => {
    it('should export only traces', async () => {
      const telemetry = new GcpOpenTelemetry({
        forceDevExport: true,
        telemetryConfig: {
          disableMetrics: true,
        },
      });
      assert.equal(telemetry['shouldExportTraces'](), true);
      assert.equal(telemetry['shouldExportMetrics'](), false);
    });

    it('should export only metrics', async () => {
      const telemetry = new GcpOpenTelemetry({
        forceDevExport: true,
        telemetryConfig: {
          disableTraces: true,
          disableMetrics: false,
        },
      });
      assert.equal(telemetry['shouldExportTraces'](), false);
      assert.equal(telemetry['shouldExportMetrics'](), true);
    });
  });

  /** Polls the in memory metric exporter until the genkit scope is found. */
  async function getGenkitMetrics(
    name: string = 'genkit',
    maxAttempts: number = 100
  ): promise<ScopeMetrics> {
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

  /** Finds a counter metric with the given name in the in memory exporter */
  async function getCounterMetric(
    metricName: string
  ): Promise<DataPoint<Counter>> {
    const genkitMetrics = await getGenkitMetrics();
    const counterMetric: SumMetricData = genkitMetrics.metrics.find(
      (e) => e.descriptor.name === metricName && e.descriptor.type === 'COUNTER'
    );
    if (counterMetric) {
      return counterMetric.dataPoints.at(-1);
    }
    assert.fail(
      `No counter metric named ${metricName} was found. Only found: ${genkitMetrics.metrics.map((e) => e.descriptor.name)}`
    );
  }

  /** Finds a histogram metric with the given name in the in memory exporter */
  async function getHistogramMetric(
    metricName: string
  ): Promise<DataPoint<Histogram>> {
    const genkitMetrics = await getGenkitMetrics();
    const histogramMetric: HistogramMetricData = genkitMetrics.metrics.find(
      (e) =>
        e.descriptor.name === metricName && e.descriptor.type === 'HISTOGRAM'
    );
    if (histogramMetric) {
      return histogramMetric.dataPoints.at(-1);
    }
    assert.fail(
      `No histogram metric named ${metricName} was found. Only found: ${genkitMetrics.metrics.map((e) => e.descriptor.name)}`
    );
  }

  /** Helper to create a flow with no inputs or outputs */
  function createFlow(name: string, fn: () => Promise<void> = async () => {}) {
    return defineFlow(
      {
        name,
        inputSchema: z.void(),
        outputSchema: z.void(),
      },
      fn
    );
  }

  /** Helper to create an action with no inputs or outputs */
  function createAction(
    name: string,
    fn: () => Promise<void> = async () => {}
  ) {
    return defineAction(
      {
        name,
        actionType: 'test',
      },
      fn
    );
  }

  /** Helper to create a model that returns the value produced by the givne
   * response function. */
  function createModel(
    name: string,
    respFn: () => Promise<GenerateResponseData>
  ) {
    return defineModel({ name }, (req) => respFn());
  }
});

class NoOpFlowStateStore implements FlowStateStore {
  state: Record<string, string> = {};

  load(id: string): Promise<FlowState | undefined> {
    return Promise.resolve(undefined);
  }

  save(id: string, state: FlowState): Promise<void> {
    return Promise.resolve();
  }

  async list(
    query?: FlowStateQuery | undefined
  ): Promise<FlowStateQueryResponse> {
    return {};
  }
}
