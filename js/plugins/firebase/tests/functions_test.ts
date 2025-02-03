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
import { afterEach, beforeEach, describe, expect, it } from '@jest/globals';
import * as express from 'express';
import { initializeApp } from 'firebase/app';
import { getFunctions, httpsCallableFromURL } from 'firebase/functions';
import { Genkit, genkit } from 'genkit';
import { runFlow, streamFlow } from 'genkit/client';
import * as getPort from 'get-port';
import * as http from 'http';
import { RequestWithAuth, noAuth, onFlow } from '../lib/functions.js';

describe('function', () => {
  let ai: Genkit;
  let server: http.Server;
  let port: number;

  beforeEach(async () => {
    ai = genkit({});

    const authPolicy = {
      provider: async (req, resp, next) => {
        (req as RequestWithAuth).auth = {
          user:
            req.header('authorization') === 'open sesame'
              ? 'Ali Baba'
              : '40 thieves',
        };
        next();
      },
      policy: (auth, input) => {
        if (auth.user !== 'Ali Baba') {
          throw new Error('not authorized');
        }
      },
    };

    const flow = onFlow(
      ai,
      {
        name: 'flow',
        authPolicy: noAuth(),
      },
      async (input) => {
        return `hi ${input}`;
      }
    );

    const streamingFlow = onFlow(
      ai,
      {
        name: 'streamingFlow',
        authPolicy: noAuth(),
      },
      async (input, { sendChunk }) => {
        sendChunk({ chubk: 1 });
        sendChunk({ chubk: 2 });
        sendChunk({ chubk: 3 });

        return `hi ${input}`;
      }
    );

    const flowWithAuth = onFlow(
      ai,
      {
        name: 'flowWithAuth',
        authPolicy: authPolicy,
      },
      async (input, { context }) => {
        return `hi ${input} - ${JSON.stringify(context?.auth)}`;
      }
    );

    const streamingFlowWithAuth = onFlow(
      ai,
      {
        name: 'streamingFlowWithAuth',
        authPolicy: authPolicy,
      },
      async (input, { context, sendChunk }) => {
        sendChunk({ chubk: 1 });
        sendChunk({ chubk: 2 });
        sendChunk({ chubk: 3 });

        return `hi ${input} - ${JSON.stringify(context?.auth)}`;
      }
    );
    const app = express();
    app.use(express.json());
    port = await getPort();
    app.post('/flow', flow);
    app.post('/flowWithAuth', flowWithAuth);
    app.post('/streamingFlow', streamingFlow);
    app.post('/streamingFlowWithAuth', streamingFlowWithAuth);
    server = app.listen(port, () => {
      console.log(`Example app listening on port ${port}`);
    });
  });

  afterEach(() => {
    server.close();
  });

  it('should call as an express route using callable functions SDK', async () => {
    const functions = getFunctions(initializeApp({}));

    const callableFlow = httpsCallableFromURL(
      functions,
      `http://localhost:${port}/flow`
    );

    const callableResponse = await callableFlow('Pavel');
    expect(callableResponse.data).toBe('hi Pavel');
  });

  it('should stream as an express route using callable functions SDK', async () => {
    const functions = getFunctions(initializeApp({}));

    const callableFlow = httpsCallableFromURL(
      functions,
      `http://localhost:${port}/streamingFlow`
    );

    const callableResponse = await callableFlow.stream('Pavel');
    const chunks: any[] = [];
    for await (const chunk of callableResponse.stream) {
      chunks.push(chunk);
    }
    expect(await callableResponse.data).toEqual('hi Pavel');
    expect(chunks).toStrictEqual([{ chubk: 1 }, { chubk: 2 }, { chubk: 3 }]);
  });

  it('should call as an express route using genkit client SDK', async () => {
    const result = await runFlow<string>({
      url: `http://localhost:${port}/flowWithAuth`,
      input: 'Pavel',
      headers: {
        Authorization: 'open sesame',
      },
    });

    expect(result).toBe('hi Pavel - {"user":"Ali Baba"}');
  });

  it('should call as an express route using genkit client SDK', async () => {
    const result = await streamFlow<string>({
      url: `http://localhost:${port}/streamingFlowWithAuth`,
      input: 'Pavel',
      headers: {
        Authorization: 'open sesame',
      },
    });

    const chunks: any[] = [];
    for await (const chunk of result.stream) {
      chunks.push(chunk);
    }

    expect(await result.output).toBe('hi Pavel - {"user":"Ali Baba"}');
    expect(chunks).toStrictEqual([{ chubk: 1 }, { chubk: 2 }, { chubk: 3 }]);
  });
});
