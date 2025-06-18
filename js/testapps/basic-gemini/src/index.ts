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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { vertexAI } from '@genkit-ai/vertexai';
import { genkit, z } from 'genkit';

const ai = genkit({
  plugins: [googleAI(), vertexAI()],
});

export const jokeFlow = ai.defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.object({ subject: z.string() }),
    outputSchema: z.object({ joke: z.string() }),
  },
  async ({ subject }) => {
    const llmResponse = await ai.generate({
      model: gemini15Flash,
      config: {
        temperature: 0.7,
      },
      output: {
        schema: z.object({ joke: z.string() }),
      },
      prompt: `Tell me a really funny joke about ${subject}`,
    });
    if (!llmResponse.output) {
      throw new Error('Failed to generate a response from the AI model. Please check the model configuration and input data.');
    }
    return llmResponse.output!;
  }
);
