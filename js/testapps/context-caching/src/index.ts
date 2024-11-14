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
import * as fs from 'fs/promises'; // Import fs to read text files
import { genkit, z } from 'genkit';
import { logger } from 'genkit/logging';

const ai = genkit({
  plugins: [googleAI()],
});

logger.setLogLevel('debug');

export const lotrFlow = ai.defineFlow(
  {
    name: 'lotrFlow',
    inputSchema: z.object({
      query: z.string().optional(),
      textFilePath: z.string(), // Add the file path to input schema
    }),
    outputSchema: z.string(),
  },
  async ({ query, textFilePath }) => {
    const defaultQuery =
      "Describe Gandalf's relationship with Frodo, referencing Gandalf quotes from the text.";

    // Read the content from the file if the path is provided
    const textContent = await fs.readFile(textFilePath, 'utf-8');

    const llmResponse = await ai.generate({
      messages: [
        {
          role: 'user',
          content: [{ text: textContent }], // Use the loaded file content here
        },
        {
          role: 'model',
          content: [
            {
              text: 'This is the first few chapters of Lord of the Rings. Can I help in any way?',
            },
          ],
          metadata: {
            cache: {
              ttlSeconds: 300,
            }, // this message is the last one to be cached.
          },
        },
      ],
      config: {
        version: 'gemini-1.5-flash-001', // Adjust for model version
      },
      model: gemini15Flash,
      prompt: query || defaultQuery,
    });

    return llmResponse.text;
  }
);
