import { loadPrompt, promptTemplate } from '@google-genkit/ai';

import { generateText } from '@google-genkit/ai/text';
import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { run, runFlow } from '@google-genkit/flow';
import { onFlow } from '@google-genkit/providers/firebase-functions';
import { configureVertexAiTextModel } from '@google-genkit/providers/llms';
import { firebase } from '@google-genkit/providers/firebase';
import { onRequest } from 'firebase-functions/v2/https';
import * as z from 'zod';

configureVertexAiTextModel({ modelName: 'gemini-pro' });

configureGenkit({
  plugins: [firebase({ projectId: getProjectId() })],
  flowStateStore: 'firestoreStores',
  traceStore: 'firestoreStores',
  enableTracingAndMetrics: true,
  logLevel: 'info',
});

export const jokeFlow = onFlow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    const prompt = await promptTemplate({
      template: loadPrompt(__dirname + '/../prompts/TellJoke.prompt'),
      variables: { subject },
    });

    return await run('call-llm', async () => {
      const llmResponse = await generateText({ prompt });

      return llmResponse.completion;
    });
  }
);

export const triggerJokeFlow2 = onRequest(
  { invoker: 'private' },
  async (req, res) => {
    const { subject } = req.query;
    console.log('req.query', req.query);
    const op = await runFlow(jokeFlow, String(subject));
    console.log('operation', op);
    res.send(op);
  }
);
