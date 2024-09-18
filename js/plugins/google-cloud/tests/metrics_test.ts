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

import { generate, GenerateResponseData } from '@genkit-ai/ai';
import { defineModel } from '@genkit-ai/ai/model';
import {
  configureGenkit,
  defineAction,
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateStore,
} from '@genkit-ai/core';
import { registerFlowStateStore } from '@genkit-ai/core/registry';
import { newTrace } from '@genkit-ai/core/tracing';
import { defineFlow, run, runAction, runFlow } from '@genkit-ai/flow';
import {
  __forceFlushSpansForTesting,
  __getMetricExporterForTesting,
  __getSpanExporterForTesting,
  build,
  googleCloud,
} from '@genkit-ai/google-cloud';
import {
  DataPoint,
  Histogram,
  HistogramMetricData,
  ScopeMetrics,
  SumMetricData,
} from '@opentelemetry/sdk-metrics';
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
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
    registerFlowStateStore('dev', async () => new NoOpFlowStateStore());
    // Wait for the telemetry plugin to be initialized
    await config.getTelemetryConfig();
  });
  beforeEach(async () => {
    __getMetricExporterForTesting().reset();
    __getSpanExporterForTesting().reset();
  });

  it('writes flow metrics', async () => {
    const testFlow = createFlow('testFlow');

    await runFlow(testFlow);
    await runFlow(testFlow);

    await getExportedSpans();

    const requestCounter = await getCounterMetric('genkit/flow/requests');
    const latencyHistogram = await getHistogramMetric('genkit/flow/latency');
    assert.equal(requestCounter.value, 2);
    assert.equal(requestCounter.attributes.name, 'testFlow');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.status, 'success');
    assert.ok(requestCounter.attributes.sourceVersion);
    assert.equal(latencyHistogram.value.count, 2);
    assert.equal(latencyHistogram.attributes.name, 'testFlow');
    assert.equal(latencyHistogram.attributes.source, 'ts');
    assert.equal(latencyHistogram.attributes.status, 'success');
    assert.ok(latencyHistogram.attributes.sourceVersion);
  });

  it('writes flow failure metrics', async () => {
    const testFlow = createFlow('testFlow', async () => {
      const nothing: { missing?: any } = { missing: 1 };
      delete nothing.missing;
      return nothing.missing.explode;
    });

    assert.rejects(async () => {
      await runFlow(testFlow);
    });

    await getExportedSpans();

    const requestCounter = await getCounterMetric('genkit/flow/requests');
    assert.equal(requestCounter.value, 1);
    assert.equal(requestCounter.attributes.name, 'testFlow');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.error, 'TypeError');
    assert.equal(requestCounter.attributes.status, 'failure');
  });

  it('writes action metrics', async () => {
    const testAction = createAction('testAction');
    const testFlow = createFlow('testFlowWithActions', async () => {
      await Promise.all([
        runAction(testAction, null),
        runAction(testAction, null),
        runAction(testAction, null),
      ]);
    });

    await runFlow(testFlow);
    await runFlow(testFlow);

    await getExportedSpans();

    const requestCounter = await getCounterMetric('genkit/action/requests');
    const latencyHistogram = await getHistogramMetric('genkit/action/latency');
    assert.equal(requestCounter.value, 6);
    assert.equal(requestCounter.attributes.name, 'testAction');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.status, 'success');
    assert.ok(requestCounter.attributes.sourceVersion);
    assert.equal(latencyHistogram.value.count, 6);
    assert.equal(latencyHistogram.attributes.name, 'testAction');
    assert.equal(latencyHistogram.attributes.source, 'ts');
    assert.equal(latencyHistogram.attributes.status, 'success');
    assert.ok(latencyHistogram.attributes.sourceVersion);
  });

  it('truncates metric dimensions', async () => {
    const testFlow = createFlow('anExtremelyLongFlowNameThatIsTooBig');

    await runFlow(testFlow);

    await getExportedSpans();

    const requestCounter = await getCounterMetric('genkit/flow/requests');
    const latencyHistogram = await getHistogramMetric('genkit/flow/latency');
    assert.equal(
      requestCounter.attributes.name,
      'anExtremelyLongFlowNameThatIsToo'
    );
    assert.equal(
      latencyHistogram.attributes.name,
      'anExtremelyLongFlowNameThatIsToo'
    );
  });

  it('writes action failure metrics', async () => {
    const testAction = createAction('testActionWithFailure', async () => {
      const nothing: { missing?: any } = { missing: 1 };
      delete nothing.missing;
      return nothing.missing.explode;
    });
    const testFlow = createFlow('testFlowWithFailingActions', async () => {
      await runAction(testAction, null);
    });

    assert.rejects(async () => {
      await runFlow(testFlow);
    });

    await getExportedSpans();

    const requestCounter = await getCounterMetric('genkit/action/requests');
    assert.equal(requestCounter.value, 1);
    assert.equal(requestCounter.attributes.name, 'testActionWithFailure');
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.status, 'failure');
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

    await getExportedSpans();

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
    for (let metric of [
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
      assert.equal(metric.attributes.status, 'success');
      assert.ok(metric.attributes.sourceVersion);
    }
  });

  it('writes generate failure metrics', async () => {
    const testModel = createModel('failingTestModel', async () => {
      const nothing: { missing?: any } = { missing: 1 };
      delete nothing.missing;
      return nothing.missing.explode;
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

    await getExportedSpans();

    const requestCounter = await getCounterMetric(
      'genkit/ai/generate/requests'
    );
    assert.equal(requestCounter.value, 1);
    assert.equal(requestCounter.attributes.modelName, 'failingTestModel');
    assert.equal(requestCounter.attributes.temperature, 1.0);
    assert.equal(requestCounter.attributes.topK, 3);
    assert.equal(requestCounter.attributes.topP, 5);
    assert.equal(requestCounter.attributes.source, 'ts');
    assert.equal(requestCounter.attributes.status, 'failure');
    assert.equal(requestCounter.attributes.error, 'TypeError');
    assert.ok(requestCounter.attributes.sourceVersion);
  });

  it('writes flow label to action metrics when running inside flow', async () => {
    const testAction = createAction('testAction');
    const flow = createFlow('flowNameLabelTestFlow', async () => {
      return await runAction(testAction, null);
    });

    await runFlow(flow);

    await getExportedSpans();

    const requestCounter = await getCounterMetric('genkit/action/requests');
    const latencyHistogram = await getHistogramMetric('genkit/action/latency');
    assert.equal(requestCounter.attributes.flowName, 'flowNameLabelTestFlow');
    assert.equal(latencyHistogram.attributes.flowName, 'flowNameLabelTestFlow');
  });

  it('writes flow label to generate metrics when running inside flow', async () => {
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
    const flow = createFlow('testFlow', async () => {
      return await generate({
        model: testModel,
        prompt: 'test prompt',
      });
    });

    await newTrace({ name: 'dev-run-action-wrapper' }, async (_, span) => {
      await runFlow(flow);
    });

    await getExportedSpans();

    const metrics = [
      await getCounterMetric('genkit/ai/generate/requests'),
      await getCounterMetric('genkit/ai/generate/input/tokens'),
      await getCounterMetric('genkit/ai/generate/output/tokens'),
      await getCounterMetric('genkit/ai/generate/input/characters'),
      await getCounterMetric('genkit/ai/generate/output/characters'),
      await getCounterMetric('genkit/ai/generate/input/images'),
      await getCounterMetric('genkit/ai/generate/output/images'),
      await getHistogramMetric('genkit/ai/generate/latency'),
    ];
    for (let metric of metrics) {
      assert.equal(metric.attributes.flowName, 'testFlow');
    }
  });

  it('writes flow paths metrics', async () => {
    const flow = createFlow('pathTestFlow', async () => {
      await run('step1', async () => {
        return await run('substep_a', async () => {
          return await run('substep_b', async () => 'res1');
        });
      });
      await run('step2', async () => 'res2');
      return;
    });

    await runFlow(flow);

    await getExportedSpans();

    const expectedPaths = new Set([
      '/{pathTestFlow,t:flow}/{step2,t:flowStep}',
      '/{pathTestFlow,t:flow}/{step1,t:flowStep}/{substep_a,t:flowStep}/{substep_b,t:flowStep}',
    ]);
    const pathCounterPoints = await getCounterDataPoints(
      'genkit/flow/path/requests'
    );
    const pathLatencyPoints = await getHistogramDataPoints(
      'genkit/flow/path/latency'
    );
    const paths = new Set(
      pathCounterPoints.map((point) => point.attributes.path)
    );
    assert.deepEqual(paths, expectedPaths);
    pathCounterPoints.forEach((point) => {
      assert.equal(point.value, 1);
      assert.equal(point.attributes.flowName, 'pathTestFlow');
      assert.equal(point.attributes.source, 'ts');
      assert.equal(point.attributes.status, 'success');
      assert.ok(point.attributes.sourceVersion);
    });
    pathLatencyPoints.forEach((point) => {
      assert.equal(point.value.count, 1);
      assert.equal(point.attributes.flowName, 'pathTestFlow');
      assert.equal(point.attributes.source, 'ts');
      assert.equal(point.attributes.status, 'success');
      assert.ok(point.attributes.sourceVersion);
    });
  });

  it('writes flow path failure metrics in root', async () => {
    const flow = createFlow('testFlow', async () => {
      const subPath = await run('sub-action', async () => {
        return 'done';
      });
      return Promise.reject(new Error('failed'));
    });

    assert.rejects(async () => {
      await runFlow(flow);
    });

    await getExportedSpans();

    const reqPoints = await getCounterDataPoints('genkit/flow/path/requests');
    const reqStatuses = reqPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(reqStatuses, [
      ['/{testFlow,t:flow}/{sub-action,t:flowStep}', 'success'],
      ['/{testFlow,t:flow}', 'failure'],
    ]);
    const latencyPoints = await getHistogramDataPoints(
      'genkit/flow/path/latency'
    );
    const latencyStatuses = latencyPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(latencyStatuses, [
      ['/{testFlow,t:flow}/{sub-action,t:flowStep}', 'success'],
      ['/{testFlow,t:flow}', 'failure'],
    ]);
  });

  it('writes flow path failure metrics in subaction', async () => {
    const flow = createFlow('testFlow', async () => {
      const subPath1 = await run('sub-action-1', async () => {
        const subPath2 = await run('sub-action-2', async () => {
          return Promise.reject(new Error('failed'));
        });
        return 'done';
      });
      return 'done';
    });

    assert.rejects(async () => {
      await runFlow(flow);
    });

    await getExportedSpans();

    const reqPoints = await getCounterDataPoints('genkit/flow/path/requests');
    const reqStatuses = reqPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(reqStatuses, [
      [
        '/{testFlow,t:flow}/{sub-action-1,t:flowStep}/{sub-action-2,t:flowStep}',
        'failure',
      ],
    ]);
    const latencyPoints = await getHistogramDataPoints(
      'genkit/flow/path/latency'
    );
    const latencyStatuses = latencyPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(latencyStatuses, [
      [
        '/{testFlow,t:flow}/{sub-action-1,t:flowStep}/{sub-action-2,t:flowStep}',
        'failure',
      ],
    ]);
  });

  it('writes flow path failure metrics in subaction', async () => {
    const flow = createFlow('testFlow', async () => {
      const subPath1 = await run('sub-action-1', async () => {
        const subPath2 = await run('sub-action-2', async () => {
          return 'done';
        });
        return Promise.reject(new Error('failed'));
      });
      return 'done';
    });

    assert.rejects(async () => {
      await runFlow(flow);
    });

    await getExportedSpans();

    const reqPoints = await getCounterDataPoints('genkit/flow/path/requests');
    const reqStatuses = reqPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(reqStatuses, [
      [
        '/{testFlow,t:flow}/{sub-action-1,t:flowStep}/{sub-action-2,t:flowStep}',
        'success',
      ],
      ['/{testFlow,t:flow}/{sub-action-1,t:flowStep}', 'failure'],
    ]);
    const latencyPoints = await getHistogramDataPoints(
      'genkit/flow/path/latency'
    );
    const latencyStatuses = latencyPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(latencyStatuses, [
      [
        '/{testFlow,t:flow}/{sub-action-1,t:flowStep}/{sub-action-2,t:flowStep}',
        'success',
      ],
      ['/{testFlow,t:flow}/{sub-action-1,t:flowStep}', 'failure'],
    ]);
  });

  it('writes flow path failure in sub-action metrics', async () => {
    const flow = createFlow('testFlow', async () => {
      const subPath1 = await run('sub-action-1', async () => {
        return 'done';
      });
      const subPath2 = await run('sub-action-2', async () => {
        return Promise.reject(new Error('failed'));
      });
      return 'done';
    });

    assert.rejects(async () => {
      await runFlow(flow);
    });

    await getExportedSpans();

    const reqPoints = await getCounterDataPoints('genkit/flow/path/requests');
    const reqStatuses = reqPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(reqStatuses, [
      ['/{testFlow,t:flow}/{sub-action-1,t:flowStep}', 'success'],
      ['/{testFlow,t:flow}/{sub-action-2,t:flowStep}', 'failure'],
    ]);
    const latencyPoints = await getHistogramDataPoints(
      'genkit/flow/path/latency'
    );
    const latencyStatuses = latencyPoints.map((p) => [
      p.attributes.path,
      p.attributes.status,
    ]);
    assert.deepEqual(latencyStatuses, [
      ['/{testFlow,t:flow}/{sub-action-1,t:flowStep}', 'success'],
      ['/{testFlow,t:flow}/{sub-action-2,t:flowStep}', 'failure'],
    ]);
  });

  describe('Configuration', () => {
    it('should export only traces', async () => {
      const plug = await build({
        telemetryConfig: {
          forceDevExport: true,
          disableMetrics: true,
        },
      });
      const gcpOt = plug.telemetry.instrumentation.value;
      assert.equal(gcpOt['shouldExportTraces'](), true);
      assert.equal(gcpOt['shouldExportMetrics'](), false);
    });

    it('should export only metrics', async () => {
      const plug = await build({
        telemetryConfig: {
          forceDevExport: true,
          disableTraces: true,
          disableMetrics: false,
        },
      });
      const gcpOt = plug.telemetry.instrumentation.value;
      assert.equal(gcpOt['shouldExportTraces'](), false);
      assert.equal(gcpOt['shouldExportMetrics'](), true);
    });
  });

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

  /** Polls the in memory metric exporter until the genkit scope is found. */
  async function getExportedSpans(
    maxAttempts: number = 200
  ): Promise<ReadableSpan[]> {
    __forceFlushSpansForTesting();
    var attempts = 0;
    while (attempts++ < maxAttempts) {
      await new Promise((resolve) => setTimeout(resolve, 50));
      const found = __getSpanExporterForTesting().getFinishedSpans();
      if (found.length > 0) {
        return found;
      }
    }
    assert.fail(`Timed out while waiting for spans to be exported.`);
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

  /**
   * Finds all datapoints for a histogram metric with the given name in the in
   * memory exporter.
   */
  async function getHistogramDataPoints(
    metricName: string
  ): Promise<Array<DataPoint<Histogram>>> {
    const genkitMetrics = await getGenkitMetrics();
    if (genkitMetrics === undefined) {
      assert.fail('Genkit metrics not found');
    } else {
      const histogramMetric = genkitMetrics.metrics.find(
        (e) =>
          e.descriptor.name === metricName && e.descriptor.type === 'HISTOGRAM'
      ) as HistogramMetricData;
      if (histogramMetric === undefined) {
        assert.fail(
          `No histogram metric named ${metricName} was found. Only found: ${genkitMetrics.metrics.map((e) => e.descriptor.name)}`
        );
      } else {
        return histogramMetric.dataPoints;
      }
    }
  }

  /** Finds a histogram metric with the given name in the in memory exporter */
  async function getHistogramMetric(
    metricName: string
  ): Promise<DataPoint<Histogram>> {
    const metric = await getHistogramDataPoints(metricName).then((points) =>
      points.at(-1)
    );
    if (metric === undefined) {
      assert.fail('Metric not found');
    } else {
      return metric;
    }
  }

  /** Helper to create a flow with no inputs or outputs */
  function createFlow(name: string, fn: () => Promise<any> = async () => {}) {
    return defineFlow(
      {
        name,
        inputSchema: z.void(),
        outputSchema: z.any(),
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
        actionType: 'model',
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
    return { flowStates: [] };
  }
}
