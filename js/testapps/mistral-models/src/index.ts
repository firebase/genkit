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
import { vertexAI } from '@genkit-ai/vertexai';
import {
  claude35Sonnet,
  mistralLarge,
  vertexAIModelGarden,
} from '@genkit-ai/vertexai/modelgarden';
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
    }),
    vertexAIModelGarden({
      location: 'us-central1',
      models: [claude35Sonnet, mistralLarge],
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

export const menuSuggestionFlow = ai.defineStreamingFlow(
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (subject, streamingCallback) => {
    const prompt = `Suggest an item for the menu of a ${subject} themed restaurant`;
    const llmResponse = await ai.generateStream({
      model: mistralLarge,
      prompt: prompt,
      tools: ['menu-suggestion'],
      config: {
        version: 'mistral-large-2407',
        temperature: 1,
      },
      // returnToolRequests: true,
    });

    if (streamingCallback) {
      for await (const chunk of llmResponse.stream) {
        // Here, you could process the chunk in some way before sending it to
        // the output stream via streamingCallback(). In this example, we output
        // the text of the chunk, unmodified.
        streamingCallback(chunk.text);
      }
    }

    return (await llmResponse.response).text;
  }
);
