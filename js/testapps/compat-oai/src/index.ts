/**
 * Copyright 2024 The Fire Company
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

import openAI, { gpt41, textEmbeddingAda002 } from '@genkit-ai/compat-oai';
import { startFlowServer } from '@genkit-ai/express';
import dotenv from 'dotenv';
import { GenerationCommonConfigSchema, genkit, z } from 'genkit';
import type { ModelInfo } from 'genkit/model';

dotenv.config();

const ai = genkit({
  plugins: [openAI({ apiKey: process.env.OPENAI_API_KEY })],
  model: gpt41,
});

export const jokeFlow = ai.defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await ai.generate({
      prompt: `tell me a joke about ${subject}`,
    });
    return llmResponse.text;
  }
);

//  genkit flow:run embedFlow \"hello world\"

export const embedFlow = ai.defineFlow(
  {
    name: 'embedFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (text) => {
    const embedding = await ai.embed({
      embedder: textEmbeddingAda002,
      content: text,
    });

    return JSON.stringify(embedding);
  }
);

const modelInfo: ModelInfo = {
  versions: ['claude-3-7-sonnet-20250219'],
  label: 'Claude - Claude 3.7 Sonnet',
  supports: {
    multiturn: true,
    tools: true,
    media: false,
    systemRole: true,
    output: ['json', 'text'],
  },
};
const schema = GenerationCommonConfigSchema.extend({});

const aiCustom = genkit({
  plugins: [
    openAI({
      apiKey: process.env.ANTHROPIC_API_KEY,
      baseURL: 'https://api.anthropic.com/v1/',
      models: [
        { name: 'claude-3-7-sonnet', info: modelInfo, configSchema: schema },
      ],
    }),
  ],
});

export const customModelFlow = aiCustom.defineFlow(
  {
    name: 'customModelFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    const llmResponse = await aiCustom.generate({
      prompt: `tell me a joke about ${subject}`,
      model: 'openai/claude-3-7-sonnet',
      config: {
        version: 'claude-3-7-sonnet-20250219',
      },
    });
    return llmResponse.text;
  }
);

startFlowServer({
  flows: [jokeFlow, embedFlow, customModelFlow],
});
