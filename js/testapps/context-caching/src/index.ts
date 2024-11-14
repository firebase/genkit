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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai'; // Import specific AI plugins/models
import * as fs from 'fs/promises'; // Import fs module to handle file operations asynchronously
import { genkit, z } from 'genkit'; // Import Genkit framework and Zod for schema validation
import { logger } from 'genkit/logging'; // Import logging utility from Genkit

const ai = genkit({
  plugins: [googleAI()], // Initialize Genkit with the Google AI plugin
});

logger.setLogLevel('debug'); // Set the logging level to debug for detailed output

export const lotrFlow = ai.defineFlow(
  {
    name: 'lotrFlow', // Define a unique name for this flow
    inputSchema: z.object({
      query: z.string().optional(), // Define a query input, which is optional
      textFilePath: z.string(), // Add the file path to input schema
    }),
    outputSchema: z.string(), // Define the expected output as a string
  },
  async ({ query, textFilePath }) => {
    const defaultQuery =
      "Describe Gandalf's relationship with Frodo, referencing Gandalf quotes from the text."; // Default query to use if none is provided

    // Read the content from the file if the path is provided
    const textContent = await fs.readFile(textFilePath, 'utf-8'); // Read the file as UTF-8 encoded text

    const llmResponse = await ai.generate({
      messages: [
        {
          role: 'user', // Represents the user's input or query
          content: [{ text: textContent }], // Use the loaded file content here
        },
        {
          role: 'model', // Represents the model's response
          content: [
            {
              text: 'This is the first few chapters of Lord of the Rings. Can I help in any way?', // Example model response
            },
          ],
          metadata: {
            cache: {
              ttlSeconds: 300, // Set the cache time-to-live for this message to 300 seconds
            }, // this message is the last one to be cached.
          },
        },
      ],
      config: {
        version: 'gemini-1.5-flash-001', // Specify the version of the model to be used
      },
      model: gemini15Flash, // Specify the model (gemini15Flash) to use for generation
      prompt: query || defaultQuery, // Use the provided query or fall back to the default query
    });

    return llmResponse.text; // Return the generated text from the model
  }
);
