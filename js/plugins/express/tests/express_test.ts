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

import express from 'express';
import { Genkit, genkit, z } from 'genkit';
import { runFlow, streamFlow } from 'genkit/client';
import { ModelAction } from 'genkit/model';
import getPort from 'get-port';
import * as http from 'http';
import assert from 'node:assert';
import { afterEach, beforeEach, describe, it } from 'node:test';
import { getFlowContext } from '../../../core/lib/auth.js';
import { handler } from '../src/index.js';

describe('telemetry', async () => {
  let server: http.Server;
  let port;

  beforeEach(async () => {
    const ai = genkit({});
    defineEchoModel(ai);

    const voidInput = ai.defineFlow('voidInput', async () => {
      return 'banana';
    });

    const stringInput = ai.defineFlow('stringInput', async (input) => {
      const { text } = await ai.generate({
        model: 'echoModel',
        prompt: input,
      });
      return text;
    });

    const objectInput = ai.defineFlow(
      { name: 'objectInput', inputSchema: z.object({ question: z.string() }) },
      async (input) => {
        const { text } = await ai.generate({
          model: 'echoModel',
          prompt: input.question,
        });
        return text;
      }
    );

    const streamingFlow = ai.defineFlow(
      {
        name: 'streamingFlow',
        inputSchema: z.object({ question: z.string() }),
      },
      async (input, sendChunk) => {
        const { text } = await ai.generate({
          model: 'echoModel',
          prompt: input.question,
          streamingCallback: sendChunk,
        });
        return text;
      }
    );

    const flowWithContext = ai.defineFlow(
      {
        name: 'flowWithContext',
        inputSchema: z.object({ question: z.string() }),
      },
      async (input) => {
        return `${input.question} - ${JSON.stringify(getFlowContext())}`;
      }
    );

    const app = express();
    app.use(express.json());
    port = await getPort();

    app.post('/voidInput', handler(voidInput));
    app.post('/stringInput', handler(stringInput));
    app.post('/objectInput', handler(objectInput));
    app.post('/streamingFlow', handler(streamingFlow));
    app.post(
      '/flowWithAuth',
      async (req, res, next) => {
        (req as any).auth = {
          user:
            req.header('authorization') === 'open sesame'
              ? 'Ali Baba'
              : '40 thieves',
        };
        next();
      },
      handler(flowWithContext, {
        authPolicy: ({ auth, flow, input, request }) => {
          assert.ok(auth, 'auth must be set');
          assert.ok(flow, 'flow must be set');
          assert.ok(input, 'input must be set');
          assert.ok(request, 'request must be set');

          if (auth.user !== 'Ali Baba') {
            throw new Error('not authorized');
          }
        },
      })
    );

    server = app.listen(port, () => {
      console.log(`Example app listening on port ${port}`);
    });
  });

  afterEach(() => {
    server.close();
  });

  describe('runFlow', () => {
    it('should call a void input flow', async () => {
      const result = await runFlow({
        url: `http://localhost:${port}/voidInput`,
      });
      assert.strictEqual(result, 'banana');
    });

    it('should run a flow with string input', async () => {
      const result = await runFlow({
        url: `http://localhost:${port}/stringInput`,
        input: 'hello',
      });
      assert.strictEqual(result, 'Echo: hello');
    });

    it('should run a flow with object input', async () => {
      const result = await runFlow({
        url: `http://localhost:${port}/objectInput`,
        input: {
          question: 'olleh',
        },
      });
      assert.strictEqual(result, 'Echo: olleh');
    });

    it('should fail a bad input', async () => {
      const result = runFlow({
        url: `http://localhost:${port}/objectInput`,
        input: {
          badField: 'hello',
        },
      });
      await assert.rejects(result, (err: Error) => {
        return err.message.includes('INVALID_ARGUMENT');
      });
    });

    it('should call a flow with auth', async () => {
      const result = await runFlow({
        url: `http://localhost:${port}/flowWithAuth`,
        input: {
          question: 'hello',
        },
        headers: {
          Authorization: 'open sesame',
        },
      });
      assert.strictEqual(result, 'hello - {"user":"Ali Baba"}');
    });

    it('should fail a flow with auth', async () => {
      const result = runFlow({
        url: `http://localhost:${port}/flowWithAuth`,
        input: {
          question: 'hello',
        },
        headers: {
          Authorization: 'thieve #24',
        },
      });
      await assert.rejects(result, (err) => {
        return (err as Error).message.includes('not authorized');
      });
    });
  });

  describe('runFlow', () => {
    it('stream a flow', async () => {
      const result = streamFlow({
        url: `http://localhost:${port}/streamingFlow`,
        input: {
          question: 'olleh',
        },
      });

      const gotChunks: any[] = [];
      for await (const chunk of result.stream()) {
        gotChunks.push(chunk);
      }

      assert.deepStrictEqual(gotChunks, [
        { content: [{ text: '3' }] },
        { content: [{ text: '2' }] },
        { content: [{ text: '1' }] },
      ]);

      assert.strictEqual(await result.output(), 'Echo: olleh');
    });
  });
});

export function defineEchoModel(ai: Genkit): ModelAction {
  return ai.defineModel(
    {
      name: 'echoModel',
    },
    async (request, streamingCallback) => {
      streamingCallback?.({
        content: [
          {
            text: '3',
          },
        ],
      });
      streamingCallback?.({
        content: [
          {
            text: '2',
          },
        ],
      });
      streamingCallback?.({
        content: [
          {
            text: '1',
          },
        ],
      });
      return {
        message: {
          role: 'model',
          content: [
            {
              text:
                'Echo: ' +
                request.messages
                  .map(
                    (m) =>
                      (m.role === 'user' || m.role === 'model'
                        ? ''
                        : `${m.role}: `) + m.content.map((c) => c.text).join()
                  )
                  .join(),
            },
          ],
        },
        finishReason: 'stop',
      };
    }
  );
}
