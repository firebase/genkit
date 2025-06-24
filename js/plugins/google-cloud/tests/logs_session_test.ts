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
  afterAll,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  jest,
} from '@jest/globals';
import type { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import * as assert from 'assert';
import { z, type GenerateResponseData, type Genkit } from 'genkit';
import { genkit, type GenkitBeta } from 'genkit/beta';
import type { ModelAction } from 'genkit/model';
import { Writable } from 'stream';
import {
  __addTransportStreamForTesting,
  __forceFlushSpansForTesting,
  __getSpanExporterForTesting,
  __useJsonFormatForTesting,
  enableGoogleCloudTelemetry,
} from '../src/index.js';

jest.mock('../src/auth.js', () => {
  const original = jest.requireActual('../src/auth.js');
  return {
    ...(original || {}),
    resolveCurrentPrincipal: jest.fn().mockImplementation(() => {
      return Promise.resolve({
        projectId: 'test',
        serviceAccountEmail: 'test@test.com',
      });
    }),
    credentialsFromEnvironment: jest.fn().mockImplementation(() => {
      return Promise.resolve({
        projectId: 'test',
        credentials: {
          client_email: 'test@genkit.com',
          private_key: '-----BEGIN PRIVATE KEY-----',
        },
      });
    }),
  };
});

describe('GoogleCloudLogs for sessions', () => {
  let logLines = '';
  const logStream = new Writable();
  logStream._write = (chunk, encoding, next) => {
    logLines = logLines += chunk.toString();
    next();
  };

  let ai: GenkitBeta;
  let testModel: ModelAction;

  beforeAll(async () => {
    process.env.GCLOUD_PROJECT = 'test';
    process.env.GENKIT_ENV = 'dev';
    __useJsonFormatForTesting();
    __addTransportStreamForTesting(logStream);

    await enableGoogleCloudTelemetry({
      projectId: 'test',
      forceDevExport: false,
      metricExportIntervalMillis: 100,
      metricExportTimeoutMillis: 100,
    });

    ai = genkit({
      // Force GCP Plugin to use in-memory metrics exporter
      plugins: [],
    });

    testModel = createModel(ai, 'testModel', async () => {
      return {
        message: {
          role: 'user',
          content: [
            {
              text: 'response',
            },
          ],
        },
        finishReason: 'stop',
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

    await waitForLogsInit(ai, logLines);
  });

  beforeEach(async () => {
    logLines = '';
    __getSpanExporterForTesting().reset();
  });
  afterAll(async () => {
    await ai.stopServers();
  });

  it('writes logs with sessionId', async () => {
    const chat = ai.chat();

    await chat.send({ model: testModel, prompt: 'Test message' });

    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));

    // Right now sessionId is applied only at the top level send.
    // We intend to eventually make the session id available on all relevant spans.
    logObjects.forEach((logBlob) => {
      if (
        logBlob.message === 'Input[send, send]' ||
        logBlob.message === 'Output[send, send]' ||
        logBlob.message === 'Paths[send]'
      ) {
        expect(logBlob.sessionId).not.toBeUndefined();
        expect(logBlob.threadName).not.toBeUndefined();
        return;
      }

      expect(logBlob.sessionId).toBeUndefined();
      expect(logBlob.threadName).toBeUndefined();
    });
  });
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

/**
 * Helper to create a model that returns the value produced by the given
 * response function.
 */
function createModel(
  genkit: Genkit,
  name: string,
  respFn: () => Promise<GenerateResponseData>
) {
  return genkit.defineModel({ name }, (req) => respFn());
}

async function waitForLogsInit(genkit: Genkit, logLines: any) {
  await import('winston');
  const testFlow = createFlow(genkit, 'testFlow');
  await testFlow();
  await getLogs(1, 100, logLines);
}

async function getLogs(
  logCount: number,
  maxAttempts: number,
  logLines: string
): Promise<string[]> {
  var attempts = 0;
  while (attempts++ < maxAttempts) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    const found = logLines
      .trim()
      .split('\n')
      .map((l) => l.trim());
    if (found.length >= logCount) {
      return found.filter((l) => l !== undefined && l !== '');
    }
  }
  assert.fail(`Waiting for logs, but none have been written.`);
}

/** Polls the in memory metric exporter until the genkit scope is found. */
async function getExportedSpans(maxAttempts = 200): Promise<ReadableSpan[]> {
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
