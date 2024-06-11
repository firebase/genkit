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

import { definePrompt, generate, renderPrompt } from '@genkit-ai/ai';
import { GenerateRequest } from '@genkit-ai/ai/model';
import { configureGenkit } from '@genkit-ai/core';
import { dotprompt, prompt } from '@genkit-ai/dotprompt';
import { googleAI } from '@genkit-ai/googleai';

configureGenkit({
  plugins: [
    googleAI({ apiKey: process.env.GOOGLE_API_KEY!, apiVersion: 'v1beta' }),
    dotprompt(),
  ],
  logLevel: 'debug',
});

// This example demonstrates using JSON mode in a prompt file

prompt('recipe', { variant: 'jsonmode' })
  .then((recipePrompt) => recipePrompt.generate({ input: { food: 'pizza' } }))
  .then((response) => {
    console.log(response.output());
  });

export const jsonJokePrompt = definePrompt(
  {
    name: 'json_joke',
  },
  async (): Promise<GenerateRequest> => {
    const promptText = `
    You are acting as a genius comedy assistant with a deep interest in data structures, particularly obscure JSON syntax rules.
    Tell a funny JSON joke.
    `;

    return {
      messages: [{ role: 'user', content: [{ text: promptText }] }],
      config: { temperature: 0.3, responseMimeType: 'application/json' },
    };
  }
);

generate(
  renderPrompt({
    prompt: jsonJokePrompt,
    input: null,
    model: 'googleai/gemini-1.5-pro-latest',
  })
).then((response) => {
  console.log(response.output());
});
