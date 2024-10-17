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
import { generate, genkit, z } from 'genkit';
import { lotr } from './content';
const ai = genkit({
  plugins: [googleAI()],
});

export const lotrFlow = ai.defineFlow(
  {
    name: 'lotrFlow',
    inputSchema: z.object({
      preprocess: z.string().optional(),
      query: z.string().optional(),
    }),
    outputSchema: z.string(),
  },
  async ({ preprocess, query }) => {
    const defaultProcess =
      'Extract all the quotes by Gandalf to Frodo into a list.';

    const defaultQuery =
      "Describe Gandalf's relationship with Frodo, referencing Gandalf quotes from the text.";

    const extractQuotesResponse = await generate({
      messages: [
        {
          role: 'user',
          content: [{ text: lotr }], // for example, the first 10 chapters of Fellowship of the Ring
        },
        {
          role: 'model',
          content: [
            {
              text: 'This is the first few chapters of Lord of the Rings. Can I help in any way?',
            },
          ],
          metadata: {
            contextCache: true, // This marks the point where caching starts
          },
        },
      ],
      config: {
        version: 'gemini-1.5-flash-001', // Adjust for model version
        contextCache: true,
      },
      model: gemini15Flash,
      prompt: preprocess || defaultProcess,
    });

    const messages = extractQuotesResponse.toHistory(); // Ensure the context history is preserved

    // Set contextCache to true for the last message in the history
    messages[messages.length - 1].metadata = {
      ...messages[messages.length - 1].metadata,
      contextCache: true,
    };

    const llmResponse = await generate({
      messages,
      model: gemini15Flash,
      config: {
        version: 'gemini-1.5-flash-001',
        contextCache: true,
      },
      prompt:
        `You will now act as a literature expert. Answer the customer's query provided below:\n` +
        (query || defaultQuery),
    });

    return llmResponse.text();
  }
);
