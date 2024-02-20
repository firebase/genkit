import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run, runFlow } from '@google-genkit/flow';
import { configureVertexAiTextModel } from '@google-genkit/providers/llms';
import { gpt35Turbo } from '@google-genkit/providers/openai';
import { geminiPro, geminiProVision } from '@google-genkit/providers/google-ai';
import * as z from 'zod';
import config from './genkit.conf';

configureVertexAiTextModel({ modelName: 'gemini-pro' });

initializeGenkit(config);

export const jokeFlow = flow(
  { name: 'jokeFlow', input: z.string(), output: z.string() },
  async (subject) => {
    return await run('call-llm', async () => {
      const model = Math.random() > 0.5 ? geminiPro : gpt35Turbo;
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
  async (imageUrl) => {
    const result = await generate({
      model: geminiProVision,
      prompt: [
        { text: 'describe the following image:' },
        { media: { url: imageUrl } },
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
