import { generate } from '@google-genkit/ai/generate';
import { getLocation, getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { run, runFlow, streamFlow } from '@google-genkit/flow';
import { firebase } from '@google-genkit/plugin-firebase';
import { onFlow } from '@google-genkit/plugin-firebase/functions';
import { geminiPro, vertexAI } from '@google-genkit/plugin-vertex-ai';
import { onRequest } from 'firebase-functions/v2/https';
import * as z from 'zod';

configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    vertexAI({ location: getLocation(), projectId: getProjectId() }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

export const jokeFlow = onFlow(
  {
    name: 'jokeFlow',
    input: z.string(),
    output: z.string(),
    httpsOptions: { invoker: 'private' },
  },
  async (subject) => {
    const prompt = `Tell me a joke about ${subject}`;

    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: geminiPro,
        prompt: prompt,
      });

      return llmResponse.text();
    });
  }
);

export const streamer = onFlow(
  {
    name: 'streamer',
    input: z.number(),
    output: z.string(),
    streamType: z.object({ count: z.number() }),
  },
  async (count, streamingCallback) => {
    console.log('streamingCallback', !!streamingCallback);
    var i = 0;
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
  { name: 'streamConsumer', input: z.void(), output: z.void() },
  async () => {
    const response = streamFlow(streamer, 5);

    for await (const chunk of response.stream()) {
      console.log('chunk', chunk);
    }

    console.log('streamConsumer done', await response.operation());
  }
);

export const triggerJokeFlow = onRequest(
  { invoker: 'private' },
  async (req, res) => {
    const { subject } = req.query;
    console.log('req.query', req.query);
    const op = await runFlow(jokeFlow, String(subject));
    console.log('operation', op);
    res.send(op);
  }
);
