import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run } from '@google-genkit/flow';
import { geminiPro } from '@google-genkit/plugin-google-genai';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        prompt: `Tell me a joke about ${subject}`,
        model: geminiPro,
      });

      return llmResponse.text();
    });
  }
);
