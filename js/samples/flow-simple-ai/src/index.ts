import { generate, tool } from '@google-genkit/ai/generate';
import { initializeGenkit } from '@google-genkit/common/config';
import { flow, run } from '@google-genkit/flow';
import * as z from 'zod';
import config from './genkit.conf';
import { geminiPro } from '@google-genkit/plugin-vertex-ai';

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

const tools = [
  tool({
    name: 'tellAFunnyJoke',
    description:
      'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
    input: z.object({ topic: z.string() }),
    output: z.string(),
    fn: async (input) => {
      return `Why did the ${input.topic} cross the road?`;
    },
  }),
];

export const jokeWithToolsFlow = flow(
  {
    name: 'jokeWithToolsFlow',
    input: z.object({ modelName: z.string(), subject: z.string() }),
    output: z.string(),
  },
  async (input) => {
    const llmResponse = await generate({
      model: input.modelName,
      tools,
      prompt: `Tell a joke about ${input.subject}.`,
    });
    return `From ${input.modelName}: ${llmResponse.text()}`;
  }
);

export const vertexStreamer = flow(
  {
    name: 'vertexStreamer',
    input: z.string(),
    output: z.string(),
  },
  async (input, streamingCallback) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: geminiPro,
        prompt: `Tell me a very long joke about ${input}.`,
        streamingCallback,
      });

      return llmResponse.text();
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
