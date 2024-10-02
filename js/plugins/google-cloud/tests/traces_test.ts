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
  __forceFlushSpansForTesting,
  __getSpanExporterForTesting,
  googleCloud,
} from '@genkit-ai/google-cloud';
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import { Genkit, genkit, run, z } from 'genkit';
import { appendSpan } from 'genkit/tracing';
import assert from 'node:assert';
import { after, before, beforeEach, describe, it } from 'node:test';

describe('GoogleCloudTracing', () => {
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
          },
        }),
      ],
      enableTracingAndMetrics: true,
      telemetry: {
        instrumentation: 'googleCloud',
        logger: 'googleCloud',
      },
    });
    // Wait for the telemetry plugin to be initialized
    await ai.getTelemetryConfig();
  });
  beforeEach(async () => {
    __getSpanExporterForTesting().reset();
  });
  after(async () => {
    await ai.stopServers();
  });

  it('writes traces', async () => {
    const testFlow = createFlow(ai, 'testFlow');

    await testFlow();

    const spans = await getExportedSpans();
    assert.equal(spans.length, 1);
    assert.equal(spans[0].name, 'testFlow');
  });

  it('Adjusts attributes to support GCP trace filtering', async () => {
    const testFlow = createFlow(ai, 'testFlow');

    await testFlow();

    const spans = await getExportedSpans();
    // Check some common attributes
    assert.equal(spans[0].attributes['genkit/name'], 'testFlow');
    assert.equal(spans[0].attributes['genkit/type'], 'flow');
    // Ensure we have no attributes with ':' because these are awkward to use in
    // Cloud Trace.
    const spanAttrKeys = Object.entries(spans[0].attributes).map(([k, v]) => k);
    for (const key in spanAttrKeys) {
      assert.equal(key.indexOf(':'), -1);
    }
  });

  it('sub actions are contained within flows', async () => {
    const testFlow = createFlow(ai, 'testFlow', async () => {
      return await run('subAction', async () => {
        return await run('subAction2', async () => {
          return 'done';
        });
      });
    });

    await testFlow();

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
    const testFlow1 = createFlow(ai, 'testFlow1');
    const testFlow2 = createFlow(ai, 'testFlow2');

    await testFlow1();
    await testFlow2();

    const spans = await getExportedSpans();
    assert.equal(spans.length, 2);
    assert.equal(spans[0].parentSpanId, undefined);
    assert.equal(spans[1].parentSpanId, undefined);
  });

  it('labels failed actions', async () => {
    const testFlow = createFlow(ai, 'badFlow', async () => {
      return await run('badAction', async () => {
        throw new Error('oh no!');
      });
    });
    try {
      await testFlow();
    } catch (e) {}

    const spans = await getExportedSpans();
    assert.equal(spans.length, 2);
    assert.equal(spans[0].name, 'badAction');
    assert.equal(spans[0].attributes['genkit/failedSpan'], 'badAction');
  });

  it('attaches additional span', async () => {
    appendSpan(
      'trace1',
      'parent1',
      { name: 'span-name', metadata: { metadata_key: 'metadata_value' } },
      { ['label_key']: 'label_value' }
    );

    const spans = await getExportedSpans();
    assert.equal(spans.length, 1);
    assert.equal(spans[0].name, 'span-name');
    assert.equal(Object.keys(spans[0].attributes).length, 3);
    assert.equal(spans[0].attributes['genkit/name'], 'span-name');
    assert.equal(spans[0].attributes['label_key'], 'label_value');
    assert.equal(
      spans[0].attributes['genkit/metadata/metadata_key'],
      'metadata_value'
    );
  });

  /** Helper to create a flow with no inputs or outputs */
  function createFlow(
    ai: Genkit,
    name: string,
    fn: () => Promise<any> = async () => {}
  ) {
    return ai.defineFlow(
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
});
