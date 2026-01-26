/**
 * Copyright 2024 The Fire Company
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

import {
  amazonTitanEmbedTextV2,
  anthropicClaude35SonnetV2,
  awsBedrock,
} from '@genkit-ai/aws-bedrock';
import { startFlowServer } from '@genkit-ai/express';
import dotenv from 'dotenv';
import { genkit, z } from 'genkit';

dotenv.config();

const ai = genkit({
  plugins: [
    awsBedrock({
      customModels: ['openai.gpt-oss-20b-1:0'], // Register custom models here
    }),
  ],
  model: anthropicClaude35SonnetV2('us'),
});

export const jokeFlow = ai.defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await ai.generate({
      prompt: `Tell me a joke about ${subject}`,
    });
    return llmResponse.text;
  }
);

export const customModelFlow = ai.defineFlow(
  {
    name: 'customModelFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await ai.generate({
      model: 'aws-bedrock/openai.gpt-oss-20b-1:0',
      prompt: `Tell me a joke about ${subject}`,
    });
    return llmResponse.text;
  }
);

export const streamingFlow = ai.defineFlow(
  {
    name: 'streamingFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const { response, stream } = ai.generateStream({
      prompt: `Write a short story about ${subject}`,
    });

    console.log('Streaming response:');

    for await (const chunk of stream) {
      console.log('Received chunk:', chunk.text);
    }

    return (await response).text;
  }
);

export const embedderFlow = ai.defineFlow(
  {
    name: 'embedderFlow',
    inputSchema: z.object({
      text: z.string(),
    }),
    outputSchema: z.object({
      embedding: z.array(z.number()),
      dimensions: z.number(),
    }),
  },
  async (input) => {
    const result = await ai.embed({
      embedder: amazonTitanEmbedTextV2,
      content: input.text,
    });

    return {
      embedding: result[0].embedding,
      dimensions: result[0].embedding.length,
    };
  }
);

startFlowServer({
  flows: [jokeFlow, customModelFlow, streamingFlow, embedderFlow],
});
