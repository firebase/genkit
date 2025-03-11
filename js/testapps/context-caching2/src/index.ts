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

import { gemini15Flash, googleAI } from '@genkit-ai/googleai'; // Import specific plugins/models for generative AI
import * as fs from 'fs/promises'; // Import file system promises for reading files
import { genkit, z } from 'genkit'; // Import Genkit framework and Zod schema validation
import { logger } from 'genkit/logging'; // Import logger for debugging and logging

// If using Node.js <18:
// import fetch from 'node-fetch'; // Install this if `fetch` is not natively available.

const ai = genkit({
  plugins: [googleAI()], // Initialize Genkit with Google AI plugin
});

logger.setLogLevel('debug'); // Set logging level to debug for detailed logs

export const warAndPeaceFlow = ai.defineFlow(
  {
    name: 'warAndPeaceFlow', // Define a unique name for this flow
    inputSchema: z.object({
      query: z.string().optional(), // Define user input schema for query, optional string
      textFilePath: z.string().optional(), // Define schema for the text file path, optional string
    }),
    outputSchema: z.string(), // Define the expected output schema, a string
  },
  async ({ query, textFilePath }) => {
    const defaultQuery =
      "Describe Pierre Bezukhov's transformation throughout the novel."; // Default query if the user doesn't provide one

    let textContent;

    if (textFilePath) {
      // Read the content from the provided file path
      textContent = await fs.readFile(textFilePath, 'utf-8');
    } else {
      // Fetch the default content from the provided link
      const response = await fetch(
        'https://www.gutenberg.org/cache/epub/2600/pg2600.txt'
      );
      if (!response.ok) {
        const errMsg = (await response.json()).error?.message || '';
        throw new Error(
          `Failed to fetch default text content: ${response.statusText}. ${errMsg}`
        );
      }
      textContent = await response.text();
    }

    // Generate a response using AI with the following parameters
    const llmResponse = await ai.generate({
      messages: [
        {
          role: 'user', // User message providing context or query
          content: [{ text: textContent }], // Include the loaded text content as an array of parts
        },
        {
          role: 'model', // Model's response to the user's query
          content: [
            {
              text: 'Here is some analysis based on the text provided.',
            },
          ],
          metadata: {
            cache: {
              ttlSeconds: 300, // Cache TTL for this specific response
            },
          },
        },
      ],
      config: {
        version: 'gemini-1.5-flash-001', // Specify the model version
        temperature: 0.7, // Control randomness in the output
        maxOutputTokens: 1000, // Limit the maximum number of tokens for the response
        topK: 50, // Limit token selection to top K probabilities
        topP: 0.9, // Apply nucleus sampling with 0.9 threshold
        stopSequences: ['END'], // Define custom sequences to stop the generation
      },
      tools: [], // No tools used in this request
      model: gemini15Flash, // Specify the generative model to use
      prompt: query || defaultQuery, // Use user's query or default query for the main task
      returnToolRequests: false, // Prevent tool requests from being returned automatically
    });

    return llmResponse.text; // Return the generated response text
  }
);
