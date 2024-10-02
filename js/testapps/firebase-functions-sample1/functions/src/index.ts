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

import { firebase } from '@genkit-ai/firebase';
import { firebaseAuth } from '@genkit-ai/firebase/auth';
import { noAuth, onFlow } from '@genkit-ai/firebase/functions';
import {
  collectUserEngagement,
  FirebaseUserEngagementSchema,
} from '@genkit-ai/firebase/user_engagement';
import { geminiPro /*, vertexAI*/ } from '@genkit-ai/vertexai';
import { AlwaysOnSampler } from '@opentelemetry/sdk-trace-base';
import { onRequest } from 'firebase-functions/v2/https';
import { genkit, run, z } from 'genkit';

const ai = genkit({
  plugins: [
    firebase({
      telemetryConfig: {
        forceDevExport: true, // do not deploy with this value
        sampler: new AlwaysOnSampler(),
        autoInstrumentation: true,
        autoInstrumentationConfig: {
          '@opentelemetry/instrumentation-fs': { enabled: false },
          '@opentelemetry/instrumentation-dns': { enabled: false },
          '@opentelemetry/instrumentation-net': { enabled: false },
        },
        metricExportIntervalMillis: 5_000, // do not deploy with this value
        metricExportTimeoutMillis: 5_000, // do not deploy with this value
      },
    }),
  ], //, vertexAI()],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
  telemetry: {
    instrumentation: 'firebase',
    logger: 'firebase',
  },
});

export const simpleFlow = onFlow(
  ai,
  {
    name: 'simpleFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    httpsOptions: {
      cors: '*',
    },
    authPolicy: noAuth(),
  },
  async (subject) => {
    return 'hello world!';
  }
);

export const jokeFlow = onFlow(
  ai,
  {
    name: 'jokeFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    httpsOptions: {
      cors: '*',
    },
    authPolicy: firebaseAuth((user) => {
      if (!user.email_verified && !user.admin) {
        throw new Error('Email not verified');
      }
    }),
  },
  async (subject) => {
    const prompt = `Tell me a joke about ${subject}`;

    return await run('call-llm', async () => {
      const llmResponse = await ai.generate({
        model: geminiPro,
        prompt: prompt,
      });

      return llmResponse.text();
    });
  }
);

export const authFlow = onFlow(
  ai,
  {
    name: 'authFlow',
    inputSchema: z.object({ uid: z.string(), input: z.string() }),
    outputSchema: z.string(),
    authPolicy: firebaseAuth((user, input) => {
      if (user.user_id !== input.uid) {
        throw new Error('User must act as themselves');
      }
    }),
  },
  async ({ input }) => input.toUpperCase()
);

export const streamer = onFlow(
  ai,
  {
    name: 'streamer',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: z.object({ count: z.number() }),
    httpsOptions: { invoker: 'private' },
    authPolicy: noAuth(),
  },
  async (count, streamingCallback) => {
    console.log('streamingCallback', !!streamingCallback);
    let i = 0;
    if (streamingCallback) {
      for (; i < count; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        streamingCallback({ count: i });
      }
    }
    return `done: ${count}, streamed: ${i} times`;
  }
);

export const streamConsumer = onFlow(
  ai,
  {
    name: 'streamConsumer',
    httpsOptions: { invoker: 'private' },
    authPolicy: noAuth(),
  },
  async () => {
    const response = streamer(5);

    for await (const chunk of response.stream) {
      console.log('chunk', chunk);
    }

    console.log('streamConsumer done', await response.output);
  }
);

export const triggerJokeFlow = onRequest(
  { invoker: 'private' },
  async (req, res) => {
    const { subject } = req.query;
    console.log('req.query', req.query);
    const op = await jokeFlow(String(subject), {
      withLocalAuthContext: { admin: true },
    });
    console.log('operation', op);
    res.send(op);
  }
);

export const collectFeedback = onRequest(async (req, res) => {
  collectUserEngagement(FirebaseUserEngagementSchema.parse(req.body));
  res.send('thanks!');
});
