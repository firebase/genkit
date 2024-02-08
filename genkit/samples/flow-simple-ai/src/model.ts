import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import {
  flow,
  run,
  runFlow
} from '@google-genkit/flow';
import { geminiPro, gpt35Turbo } from '@google-genkit/providers/models';
import * as z from 'zod';

initializeGenkit()

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string(), local: true },
  async (subject) => {
    return await run('call-llm', async () => {
      const model =
        Math.random() > 0.5
          ? geminiPro
          : gpt35Turbo;
      const llmResponse = await generate({
        model,
        prompt: `Tell a joke about ${subject}.`,
      });

      return `From ${
        model.info?.label
      }: ${llmResponse.text()}`;
    });
  }
);

async function main() {
  const operation = await runFlow(jokeFlow, 'banana');
  console.log('Operation', operation);
}

main();
