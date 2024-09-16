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
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateStore,
  configureGenkit,
} from '@genkit-ai/core';
import { registerFlowStateStore } from '@genkit-ai/core/registry';
import { defineFlow, run, runFlow } from '@genkit-ai/flow';
import {
  __forceFlushSpansForTesting,
  __getSpanExporterForTesting,
  googleCloud,
} from '@genkit-ai/google-cloud';
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import assert from 'node:assert';
import { before, beforeEach, describe, it } from 'node:test';
import { z } from 'zod';

describe('GoogleCloudTracing', () => {
  before(async () => {
    process.env.GENKIT_ENV = 'dev';
    const config = configureGenkit({
      // Force GCP Plugin to use in-memory metrics exporter
      plugins: [
        googleCloud({
          projectId: 'test',
          telemetryConfig: {
            forceDevExport: false,
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
    __getSpanExporterForTesting().reset();
  });

  it('writes traces', async () => {
    const testFlow = createFlow('testFlow');

    await runFlow(testFlow);

    const spans = await getExportedSpans();
    assert.equal(spans.length, 1);
    assert.equal(spans[0].name, 'testFlow');
  });

  it('Adjusts attributes to support GCP trace filtering', async () => {
    const testFlow = createFlow('testFlow');

    await runFlow(testFlow);

    const spans = await getExportedSpans();
    // Check some common attributes
    assert.equal(spans[0].attributes['genkit/name'], 'testFlow');
    assert.equal(spans[0].attributes['genkit/type'], 'flow');
    // Ensure we have no attributes with ':' because these are awkward to use in
    // Cloud Trace.
    const spanAttrKeys = Object.entries(spans[0].attributes).map(([k, v]) => k);
    for (key in spanAttrKeys) {
      assert.equal(key.indexOf(':'), -1);
    }
  });

  it('sub actions are contained within flows', async () => {
    const testFlow = createFlow('testFlow', async () => {
      return await run('subAction', async () => {
        return await run('subAction2', async () => {
          return 'done';
        });
      });
    });

    await runFlow(testFlow);

    const spans = await getExportedSpans();
    assert.equal(spans.length, 3);
    assert.equal(spans[2].name, 'testFlow');
    assert.equal(spans[2].parentSpanId, undefined);
    assert.equal(spans[1].name, 'subAction');
    assert.equal(spans[1].parentSpanId, spans[2].spanContext().spanId);
    assert.equal(spans[0].name, 'subAction2');
    assert.equal(spans[0].parentSpanId, spans[1].spanContext().spanId);
  });

  it('different flows run independently', async () => {
    const testFlow1 = createFlow('testFlow1');
    const testFlow2 = createFlow('testFlow2');

    await runFlow(testFlow1);
    await runFlow(testFlow2);

    const spans = await getExportedSpans();
    assert.equal(spans.length, 2);
    assert.equal(spans[0].parentSpanId, undefined);
    assert.equal(spans[1].parentSpanId, undefined);
  });

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

  /** Polls the in memory metric exporter until the genkit scope is found. */
  async function getExportedSpans(
    maxAttempts: number = 200
  ): promise<ReadableSpan[]> {
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
