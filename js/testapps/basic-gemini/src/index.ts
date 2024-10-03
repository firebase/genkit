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
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
import {
  gemini15Flash as gemini15FlashGoogleAi,
  googleAI,
} from '@genkit-ai/googleai';

// Import models from the Google AI plugin. The Google AI API provides access to

import {
  gemini15Flash as gemini15FlashVertexAi,
  vertexAI,
} from '@genkit-ai/vertexai';

const provider = process.env.PROVIDER || 'vertexai';

configureGenkit({
  plugins: [vertexAI(), googleAI()],
  // Log debug output to tbe console.
  logLevel: 'debug',
  // Perform OpenTelemetry instrumentation and enable trace collection.
  enableTracingAndMetrics: true,
});

const jokeSubjectGenerator = defineTool(
  {
    name: 'jokeSubjectGenerator',
    description: 'can be called to generate a subject for a joke',
    inputSchema: z.object({ input: z.string() }),
    outputSchema: z.string(),
  },
  async (input) => {
    throw new Error('banana');
    return 'banana';
  }
);

// Define a simple flow that prompts an LLM to generate menu suggestions.
export const jokeFlow = defineFlow(
  {
    name: 'jokeFlow',
    inputSchema: z.object({ provider: z.enum(['vertexai', 'googleai']) }),
    outputSchema: z.any(),
  },
  async ({ provider }) => {
    // Construct a request and send it to the model API.
    if (provider === 'vertexai') {
      const llmResponse = await generate({
        model: gemini15FlashVertexAi,
        config: {
          temperature: 2,
        },
        output: {
          schema: z.object({ jokeSubject: z.string() }),
        },
        tools: [jokeSubjectGenerator],
        prompt: `come up with a subject to joke about (using the function provided)`,
      });

      return llmResponse.output();
    } else {
      const llmResponse = await generate({
        model: gemini15FlashGoogleAi,
        config: {
          temperature: 2,
        },
        output: {
          schema: z.object({ jokeSubject: z.string() }),
        },
        tools: [jokeSubjectGenerator],
        prompt: `come up with a subject to joke about (using the function provided)`,
      });
      return llmResponse.output();
    }

    // Handle the response from the model API. In this sample, we just convert
    // it to a string, but more complicated flows might coerce the response into
  }
);

export const streamingFlow = defineFlow(
  {
    name: 'streamingFlow',
    inputSchema: z.object({ provider: z.enum(['vertexai', 'googleai']) }),
    outputSchema: z.any(),
  },
  async ({ provider }) => {
    let count = 0;

    if (provider === 'vertexai') {
      // Construct a request and send it to the model API.
      const llmResponse = await generate({
        model: gemini15FlashVertexAi,
        config: {
          temperature: 2,
        },
        output: {
          schema: z.array(
            z.object({
              name: z.string(),
              age: z.number(),
              description: z.string(),
              personal_statement: z.string(),
            })
          ),
        },
        tools: [jokeSubjectGenerator],
        prompt: `come up with some test user data. 10 users long`,
        streamingCallback: (chunk) => {
          count++;
          const output = chunk.text();
          console.log(`chunk ${count}`, output);
          return output;
        },
      });

      return llmResponse.output()!;
    } else {
      const llmResponse = await generate({
        model: gemini15FlashGoogleAi,
        config: {
          temperature: 2,
        },
        output: {
          schema: z.array(
            z.object({
              name: z.string(),
              age: z.number(),
              description: z.string(),
              personal_statement: z.string(),
            })
          ),
        },
        tools: [jokeSubjectGenerator],
        prompt: `come up with some test user data. 10 users long`,
        streamingCallback: (chunk) => {
          count++;
          const output = chunk.text();
          console.log(`chunk ${count}`, output);
          return output;
        },
      });
      return llmResponse.output()!;
    }
  }
);

// Start a flow server, which exposes your flows as HTTP endpoints. This call
// must come last, after all of your plug-in configuration and flow definitions.
// You can optionally specify a subset of flows to serve, and configure some
// HTTP server options, but by default, the flow server serves all defined flows.
startFlowsServer();
