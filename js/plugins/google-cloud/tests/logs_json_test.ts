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
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import * as assert from 'assert';
import { GenerateResponseData, Genkit, genkit, z } from 'genkit';
import { ModelAction } from 'genkit/model';
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

describe('GoogleCloudLogs with json', () => {
  let logLines = '';
  const logStream = new Writable();
  logStream._write = (chunk, encoding, next) => {
    logLines = logLines += chunk.toString();
    next();
  };

  let ai: Genkit;
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
          role: 'model',
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

  it('writes logs with sessionId when present', async () => {
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

  it('writes common log attributes', async () => {
    await ai.generate({
      model: testModel,
      prompt: `Some prompt`,
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });
    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));

    logObjects.forEach((logBlob) => {
      expect(logBlob['logging.googleapis.com/spanId']).not.toBeUndefined();
      expect(logBlob['logging.googleapis.com/trace']).not.toBeUndefined();
      expect(
        logBlob['logging.googleapis.com/trace_sampled']
      ).not.toBeUndefined();
    });
  });

  it('writes expected Input log attributes', async () => {
    await ai.generate({
      model: testModel,
      prompt: `Some prompt`,
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });
    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));
    var verifiedActionLog = false;
    var verifiedLLMLog = false;

    logObjects.forEach((logBlob) => {
      // action wrapper
      if (logBlob.message.startsWith('Input[generate, generate]')) {
        expect(logBlob.path).toEqual('generate');
        expect(logBlob.qualifiedPath).toEqual('/{generate,t:helper}');
        expect(logBlob.featureName).toEqual('generate');
        expect(logBlob.content).not.toBeUndefined();
        verifiedActionLog = true;
        return;
      }

      // generate request
      if (
        logBlob.message.startsWith('Input[generate > testModel, testModel]')
      ) {
        expect(logBlob.model).toEqual('testModel');
        expect(logBlob.path).toEqual('generate > testModel');
        expect(logBlob.qualifiedPath).toEqual(
          '/{generate,t:helper}/{testModel,t:action,s:model}'
        );
        expect(logBlob.featureName).toEqual('generate');
        expect(logBlob.content).toEqual('Some prompt');
        expect(logBlob.contentType).toEqual('text');
        expect(logBlob.role).toEqual('user');
        expect(logBlob.partIndex).toEqual(0);
        expect(logBlob.totalParts).toEqual(1);
        expect(logBlob.messageIndex).toEqual(0);
        expect(logBlob.totalMessages).toEqual(1);
        verifiedLLMLog = true;
      }
    });
    expect(verifiedActionLog).toBe(true);
    expect(verifiedLLMLog).toBe(true);
  });

  it('writes expected Output log attributes', async () => {
    await ai.generate({
      model: testModel,
      prompt: `Some prompt`,
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });
    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));
    var verifiedActionLog = false;
    var verifiedLLMLog = false;

    logObjects.forEach((logBlob) => {
      if (logBlob.message.startsWith('Output[generate, generate]')) {
        expect(logBlob.path).toEqual('generate');
        expect(logBlob.qualifiedPath).toEqual('/{generate,t:helper}');
        expect(logBlob.featureName).toEqual('generate');
        expect(logBlob.content).not.toBeUndefined();
        verifiedActionLog = true;
        return;
      }

      if (
        logBlob.message.startsWith('Output[generate > testModel, testModel]')
      ) {
        expect(logBlob.model).toEqual('testModel');
        expect(logBlob.path).not.toBeUndefined();
        expect(logBlob.qualifiedPath).toEqual(
          '/{generate,t:helper}/{testModel,t:action,s:model}'
        );
        expect(logBlob.featureName).toEqual('generate');
        // We won't get a content type on all output logs because of the odd behavior
        // of direct generate calls where we serialize the json blob into the content
        // of the top level call. This is verified in other tests.
        expect(logBlob.content).toEqual('response');
        expect(logBlob.contentType).toEqual('text');
        expect(logBlob.role).toEqual('model');
        expect(logBlob.partIndex).toEqual(0);
        expect(logBlob.totalParts).toEqual(1);
        expect(logBlob.candidateIndex).toEqual(0);
        expect(logBlob.totalCandidates).toEqual(1);
        expect(logBlob.messageIndex).toEqual(0);
        expect(logBlob.finishReason).toEqual('stop');
        verifiedLLMLog = true;
      }
    });
    expect(verifiedActionLog).toBe(true);
    expect(verifiedLLMLog).toBe(true);
  });

  it('writes expected Path log attributes', async () => {
    const testFlow = createFlow(ai, 'testFlowPaths', async () => {
      return ai.generate({
        model: testModel,
        prompt: `Some prompt`,
        config: {
          temperature: 1.0,
          topK: 3,
          topP: 5,
          maxOutputTokens: 7,
        },
      });
    });
    await testFlow();

    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));
    var verifiedLog = false;

    logObjects.forEach((logBlob) => {
      if (logBlob.message.startsWith('Paths[')) {
        expect(logBlob.flowName).toEqual('testFlowPaths');
        expect(logBlob.paths).toHaveLength(1);
        verifiedLog = true;
      }
    });
    expect(verifiedLog).toBe(true);
  });

  it('writes expected Config log attributes', async () => {
    await ai.generate({
      model: testModel,
      prompt: `Some prompt`,
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });

    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));
    var verifiedLog = false;
    logObjects.forEach((logBlob) => {
      if (logBlob.message.startsWith('Config[')) {
        expect(logBlob.featureName).toEqual('generate');
        expect(logBlob.model).toEqual('testModel');
        expect(logBlob.path).toEqual('generate > testModel');
        expect(logBlob.qualifiedPath).toEqual(
          '/{generate,t:helper}/{testModel,t:action,s:model}'
        );
        expect(logBlob.source).toEqual('ts');
        expect(logBlob.sourceVersion).not.toBeUndefined();
        expect(logBlob.temperature).toEqual(1);
        expect(logBlob.topK).toEqual(3);
        expect(logBlob.topP).toEqual(5);
        expect(logBlob.maxOutputTokens).toEqual(7);
        verifiedLog = true;
      }
    });
    expect(verifiedLog).toBe(true);
  });

  it('writes json contentType to log attributes', async () => {
    const jsonModel = createModel(ai, 'jsonModel', async () => {
      return {
        message: {
          role: 'model',
          content: [
            {
              data: '{"this": "is", "a": ["json", "object"]}',
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

    await ai.generate({
      model: jsonModel,
      prompt: 'Some prompt',
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });
    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));

    logObjects.forEach((logBlob) => {
      if (
        logBlob.message.startsWith('Input[generate > jsonModel, jsonModel]')
      ) {
        expect(logBlob.contentType).toEqual('text');
        return;
      }

      if (
        logBlob.message.startsWith('Output[generate > jsonModel, jsonModel]')
      ) {
        expect(logBlob.contentType).toEqual('json');
        return;
      }

      // For generate calls in isolation with propagate the full json blob to the top level Output[generate, generate] log as a string.
      // This means that we will not get a contentType on the top level log, only on the model specific log
      // We may eventually want to change how that works, but for now this test codifies the behavior.
      expect(logBlob.contentType).toBeUndefined();
    });
  });

  it('writes image contentType to log attributes', async () => {
    const imgModel = createModel(ai, 'imgModel', async () => {
      return {
        message: {
          role: 'model',
          content: [
            {
              media: {
                url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAIAAAACDbGyAAAAW0lEQVR4nAFQAK//AFmzErKgBw+nYq55+x/3bADQioQvNd9rfCyr9TfFWm4C4Iqnuz+52CBKBfwmIZxUAfMvkaAVJ2s5E6n59d06OgCL6UKYtDPEGLn1F2X/RRDCuSTKnOybSAAAAABJRU5ErkJggg==',
                contentType: 'image/png',
              },
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

    await ai.generate({
      model: imgModel,
      messages: [
        {
          role: 'user',
          content: [
            {
              text: 'Can you describe this image by generating an infographic?\n',
            },
            {
              media: {
                contentType: 'image/png',
                url: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAIAAAACDbGyAAAAW0lEQVR4nAFQAK//AFmzErKgBw+nYq55+x/3bADQioQvNd9rfCyr9TfFWm4C4Iqnuz+52CBKBfwmIZxUAfMvkaAVJ2s5E6n59d06OgCL6UKYtDPEGLn1F2X/RRDCuSTKnOybSAAAAABJRU5ErkJggg==',
              },
            },
          ],
        },
      ],
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });
    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));

    logObjects.forEach((logBlob) => {
      if (
        logBlob.message.startsWith(
          'Input[generate > imgModel, imgModel] (part 1 of 2)'
        )
      ) {
        expect(logBlob.contentType).toEqual('text');
        return;
      }

      if (
        logBlob.message.startsWith(
          'Input[generate > imgModel, imgModel] (part 2 of 2)'
        )
      ) {
        expect(logBlob.contentType).toEqual('image/png');
        return;
      }

      if (logBlob.message.startsWith('Output[generate > imgModel, imgModel]')) {
        expect(logBlob.contentType).toEqual('image/png');
        return;
      }

      // For generate calls in isolation with propagate the full json blob to the top level Output[generate, generate] log as a string.
      // This means that we will not get a contentType on the top level log, only on the model specific log
      // We may eventually want to change how that works, but for now this test codifies the behavior.
      expect(logBlob.contentType).toBeUndefined();
    });
  });

  it('writes unknown contentType to log attributes', async () => {
    const unknownModel = createModel(ai, 'unknownModel', async () => {
      return {
        message: {
          role: 'model',
          content: [
            {
              toolResponse: {
                name: 'myAwesomeTool',
                output: { this: 'is a tool result' },
              },
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

    await ai.generate({
      model: unknownModel,
      prompt: 'Some prompt',
      config: {
        temperature: 1.0,
        topK: 3,
        topP: 5,
        maxOutputTokens: 7,
      },
    });
    await getExportedSpans();

    const logMessages = await getLogs(1, 100, logLines);
    const logObjects = logMessages.map((l) => JSON.parse(l as string));

    logObjects.forEach((logBlob) => {
      if (
        logBlob.message.startsWith(
          'Input[generate > unknownModel, unknownModel]'
        )
      ) {
        expect(logBlob.contentType).toEqual('text');
        return;
      }

      if (
        logBlob.message.startsWith(
          'Output[generate > unknownModel, unknownModel]'
        )
      ) {
        expect(logBlob.contentType).toEqual('<unknown content type>');
        return;
      }

      // For generate calls in isolation we propagate the full json blob to the top level Output[generate, generate] log as a string.
      // This means that we will not get a contentType on the top level log, only on the model specific log
      // We may eventually want to change how that works, but for now this test codifies the behavior.
      expect(logBlob.contentType).toBeUndefined();
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
): Promise<String[]> {
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
