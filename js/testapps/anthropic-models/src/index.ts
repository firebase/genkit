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

// Import models from the Vertex AI plugin. The Vertex AI API provides access to
// several generative models. Here, we import Gemini 1.5 Flash.
import { claude35Sonnet, vertexAI } from '@genkit-ai/vertexai';
// Import the Genkit core libraries and plugins.
import { genkit, z } from 'genkit';

// Import models from the Vertex AI plugin. The Vertex AI API provides access to
// several generative models. Here, we import Gemini 1.5 Flash.

const ai = genkit({
  plugins: [
    // Load the Vertex AI plugin. You can optionally specify your project ID
    // by passing in a config object; if you don't, the Vertex AI plugin uses
    // the value from the GCLOUD_PROJECT environment variable.
    vertexAI({
      location: 'europe-west1',
      modelGardenModels: [claude35Sonnet],
    }),
  ],
});

ai.defineTool(
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
  async () => {
    return {
      menuItems: [`Appetizer: Meow Salad`],
    };
  }
);

// Define a simple flow that prompts an LLM to generate menu suggestions.
export const menuSuggestionFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.string(),
    outputSchema: z.array(z.any()),
  },
  async (subject) => {
    const prompt = `Suggest an item for the menu of a ${subject} themed restaurant`;
    const llmResponse = await ai.generate({
      model: claude35Sonnet,
      prompt: prompt,
      tools: ['menu-suggestion'],
      config: {
        temperature: 1,
      },
      returnToolRequests: true,
    });

    return llmResponse.toolRequests();
  }
);
