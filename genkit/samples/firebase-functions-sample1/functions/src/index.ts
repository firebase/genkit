import { generate } from '@google-genkit/ai/generate';
import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { run, runFlow } from '@google-genkit/flow';
import { firebase } from '@google-genkit/providers/firebase';
import { onFlow } from '@google-genkit/providers/firebase-functions';
import { geminiPro, googleAI } from '@google-genkit/providers/google-ai';
import { onRequest } from 'firebase-functions/v2/https';
import * as z from 'zod';

configureGenkit({
  plugins: [firebase({ projectId: getProjectId() }), googleAI()],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

export const jokeFlow = onFlow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
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
