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

import { generate, generateStream, retrieve } from '@genkit-ai/ai';
import { defineTool } from '@genkit-ai/ai/tool';
import { initializeGenkit } from '@genkit-ai/core';
import { defineFirestoreRetriever } from '@genkit-ai/firebase';
import { defineFlow, run } from '@genkit-ai/flow';
import { geminiPro as googleGeminiPro } from '@genkit-ai/googleai';
import { geminiPro, textEmbeddingGecko } from '@genkit-ai/vertexai';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import * as z from 'zod';
import config from './genkit.config.js';

initializeGenkit(config);

const app = initializeApp();

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

export const jokeFlowSimple = defineFlow(
  {
    name: 'jokeFlowSimple',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    return await run('call-llm', async () => {
      const llmResponse = await generate({
        model: googleGeminiPro,
        prompt: `Tell a joke about ${input}.`,
      });
      return llmResponse.text();
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

export const streamFlow = defineFlow(
  {
    name: 'streamFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (prompt, streamingCallback) => {
    const { response, stream } = await generateStream({
      model: geminiPro,
      prompt,
    });

    if (streamingCallback) {
      for await (const chunk of stream()) {
        streamingCallback(chunk.content[0].text!);
      }
    }

    return (await response()).text();
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
      modelName: z.enum([geminiPro.name, googleGeminiPro.name]),
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

const destinationsRetriever = defineFirestoreRetriever({
  name: 'destinationsRetriever',
  firestore: getFirestore(app),
  collection: 'destinations',
  contentField: 'knownFor',
  embedder: textEmbeddingGecko,
  vectorField: 'embedding',
});

export const searchDestinations = defineFlow(
  {
    name: 'searchDestinations',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    const docs = await retrieve({
      retriever: destinationsRetriever,
      query: input,
      options: { limit: 5 },
    });

    const result = await generate({
      model: geminiPro,
      prompt: `Give me a list of vacation options based on the provided context. Use only the options provided below, and describe how it fits with my query.
      
Query: ${input}

Available Options:\n- ${docs.map((d) => `${d.metadata!.name}: ${d.text()}`).join('\n- ')}`,
    });

    return result.text();
  }
);
