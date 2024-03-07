import { generate } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run } from '@google-genkit/flow';
import * as z from 'zod';
import config from './genkit.conf';

initializeGenkit(config);

export const jokeFlow = flow(
  {
    name: 'jokeFlow',
    input: z.object({ modelName: z.string(), subject: z.string() }),
    output: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: input.modelName,
        prompt: `Tell a joke about ${input.subject}.`,
      });
      return `From ${input.modelName}: ${llmResponse.text()}`;
    });
  }
);

export const drawPictureFlow = flow(
  {
    name: 'drawPictureFlow',
    input: z.object({ modelName: z.string(), object: z.string() }),
    output: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: input.modelName,
        prompt: `Draw a picture of a ${input.object}.`,
      });
      return `From ${
        input.modelName
      }: Here is a picture of a cat: ${llmResponse.text()}`;
    });
  }
);

export const vertexStreamer = flow(
  {
    name: 'vertexStreamer',
    input: z.object({ modelName: z.string(), subject: z.string() }),
    output: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: input.modelName,
        prompt: `Tell me a very long joke about ${input.subject}.`,
        streamingCallback: (c) => console.log('chunk', c),
      });

      return `From ${input.modelName}: ${llmResponse.text()}`;
    });
  }
);

export const multimodalFlow = flow(
  {
    name: 'multimodalFlow',
    input: z.object({ modelName: z.string(), imageUrl: z.string() }),
    output: z.string(),
  },
  async (input) => {
    const result = await generate({
      model: input.modelName,
      prompt: [
        { text: 'describe the following image:' },
        { media: { url: input.imageUrl, contentType: 'image/jpeg' } },
      ],
    });
    return result.text();
  }
);
