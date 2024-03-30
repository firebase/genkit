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

import { generate } from '@genkit-ai/ai';
import { defineTool } from '@genkit-ai/ai/tool';
import { initializeGenkit } from '@genkit-ai/core/config';
import { defineFlow, run } from '@genkit-ai/flow';
import { geminiPro as googleGeminiPro } from '@genkit-ai/plugin-google-genai';
import { gpt35Turbo, gpt4, gpt4Turbo } from '@genkit-ai/plugin-openai';
import { geminiPro } from '@genkit-ai/plugin-vertex-ai';
import * as z from 'zod';
import config from './genkit.config';

initializeGenkit(config);

export const jokeFlow = defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.object({
      modelName: z.string(),
      modelVersion: z.string().optional(),
      subject: z.string(),
    }),
    outputSchema: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: input.modelName,
        config: { version: input.modelVersion },
        prompt: `Tell a joke about ${input.subject}.`,
      });
      return `From ${input.modelName}: ${llmResponse.text()}`;
    });
  }
);

export const drawPictureFlow = defineFlow(
  {
    name: 'drawPictureFlow',
    inputSchema: z.object({ modelName: z.string(), object: z.string() }),
    outputSchema: z.string(),
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
  defineTool(
    {
      name: 'tellAFunnyJoke',
      description:
        'Tells jokes about an input topic. Use this tool whenever user asks you to tell a joke.',
      inputSchema: z.object({ topic: z.string() }),
      outputSchema: z.string(),
    },
    async (input) => {
      return `Why did the ${input.topic} cross the road?`;
    }
  ),
];

export const jokeWithToolsFlow = defineFlow(
  {
    name: 'jokeWithToolsFlow',
    inputSchema: z.object({
      modelName: z.enum([
        geminiPro.name,
        gpt4Turbo.name,
        googleGeminiPro.name,
        gpt35Turbo.name,
        gpt4.name,
      ]),
      subject: z.string(),
    }),
    outputSchema: z.string(),
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

export const vertexStreamer = defineFlow(
  {
    name: 'vertexStreamer',
    inputSchema: z.string(),
    outputSchema: z.string(),
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

export const multimodalFlow = defineFlow(
  {
    name: 'multimodalFlow',
    inputSchema: z.object({ modelName: z.string(), imageUrl: z.string() }),
    outputSchema: z.string(),
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
