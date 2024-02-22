import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run, runFlow } from '@google-genkit/flow';
import { geminiPro, geminiProVision } from '@google-genkit/plugin-vertex-ai';

import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    return await run('call-llm', async () => {
      const model = geminiPro;
      const llmResponse = await generate({
        model,
        prompt: `Tell a joke about ${subject}.`,
      });

      return `From ${model.info?.label}: ${llmResponse.text()}`;
    });
  }
);

export const multimodalFlow = flow(
  { name: 'multimodalFlow', input: z.string(), output: z.string() },
  async (imageUrl: string) => {
    const result = await generate({
      model: geminiProVision,
      prompt: [
        { text: 'describe the following image:' },
        { media: { url: imageUrl, contentType: 'image/jpeg' } },
      ],
    });

    return result.text();
  }
);

async function main() {
  console.log('running joke flow...');
  const operation = await runFlow(jokeFlow, 'banana');
  console.log('Joke:', operation);
  console.log('running multimodal flow...');
  const multimodalOperation = await runFlow(
    multimodalFlow,
    'https://picsum.photos/200'
  );
  console.log('Multimodal:', multimodalOperation);
}

main().catch(console.error);
