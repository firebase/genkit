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

import * as z from 'zod';

// Import the Genkit core libraries and plugins.
import { defineTool, generate } from '@genkit-ai/ai';
import { configureGenkit } from '@genkit-ai/core';
import { claude35Sonnet, vertexAI } from '@genkit-ai/vertexai';

// Import models from the Vertex AI plugin. The Vertex AI API provides access to
// several generative models. Here, we import Gemini 1.5 Flash.

// From the Firebase plugin, import the functions needed to deploy flows using
// Cloud Functions.
import { defineFlow } from '@genkit-ai/flow';

configureGenkit({
  plugins: [
    // Load the Vertex AI plugin. You can optionally specify your project ID
    // by passing in a config object; if you don't, the Vertex AI plugin uses
    // the value from the GCLOUD_PROJECT environment variable.
    vertexAI({
      location: 'europe-west1',
      modelGardenModels: [claude35Sonnet],
    }),
  ],

  // Log debug output to tbe console.
  logLevel: 'debug',
  // Perform OpenTelemetry instrumentation and enable trace collection.
  enableTracingAndMetrics: true,
});

// Define a simple flow that prompts an LLM to generate menu suggestions.
export const menuSuggestionFlow = defineFlow(
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject) => {
    defineTool(
      {
        name: 'menu-suggestion',
        description: 'Generate a menu suggestion for a themed restaurant',
        inputSchema: z.object({
          subject: z.string(),
        }),
        outputSchema: z.object({
          menuItems: z.array(z.string()),
        }),
      },
      async (subject) => {
        return {
          menuItems: [
            `Appetizer: ${subject} Salad`,
            `Main Course: ${subject} Burger`,
            `Dessert: ${subject} Pie`,
          ],
        };
      }
    );

    // Construct a request and send it to the model API.
    const prompt = `Suggest an item for the menu of a ${subject} themed restaurant`;
    const llmResponse = await generate({
      model: claude35Sonnet,
      prompt: prompt,
      tools: ['menu-suggestion'],
      config: {
        temperature: 1,
      },
    });

    // Handle the response from the model API. In this sample, we just
    // convert it to a string, but more complicated flows might coerce the
    // response into structured output or chain the response into another
    // LLM call, etc.
    return llmResponse.text();
  }
);
