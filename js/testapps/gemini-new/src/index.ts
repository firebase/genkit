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

import { genkit, z } from 'genkit';
//import { vertexAI, googleAI } from '@genkit-ai/google-genai';
//import { vertexAI } from '@genkit-ai/google-genai';
import { googleAI } from '@genkit-ai/google-genai';

const ai = genkit({
  //plugins: [googleAI(), vertexAI()],
  plugins: [googleAI()],
});

const jokeSubjectGenerator = ai.defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'Can be called to generate a subject for a joke',
  },
  async () => {
    return 'banana';
  }
);

export const jokeFlow = ai.defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.object({
      modelName: z.string().default('googleai/gemini-2.5-pro-exp-03-25'),
      modelVersion: z.string().optional().default('gemini-2.5-pro-exp-03-25'),
      subject: z.string().default('bananas'),
    }),
    outputSchema: z.string(),
  },
  async (input) => {
    const llmResponse = await ai.generate({
      model: input.modelName,
      config: { version: input.modelVersion },
      prompt: `Tell a joke about ${input.subject}.`,
    });
    return `From ${input.modelName}: ${llmResponse.text}`;
  }
);
