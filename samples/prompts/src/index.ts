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
import { generate } from '@genkit-ai/ai';
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow, startFlowsServer } from '@genkit-ai/flow';
import { googleAI } from '@genkit-ai/googleai';

// Import models from the Google AI plugin. The Google AI API provides access to
// several generative models. Here, we import Gemini 1.5 Flash.
import { defineDotprompt } from '@genkit-ai/dotprompt';

configureGenkit({
  plugins: [
    googleAI(), //Provide the key via the GOOGLE_GENAI_API_KEY environment variable or arg { apiKey: 'yourkey'}
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

defineFlow(
  {
    name: 'simplePrompt',
  },
  () =>
    generate({
      model: 'googleai/gemini-1.5-flash-latest',
      prompt: 'You are a helpful AI assistant named Walt, say hello',
    })
);

defineFlow(
  {
    name: 'simpleTemplate',
  },
  () => {
    function helloPrompt(name: string) {
      return `You are a helpful AI assistant named Walt. Say hello to ${name}.`;
    }

    return generate({
      model: 'googleai/gemini-1.5-flash-latest',
      prompt: helloPrompt('Fred'),
    });
  }
);

const helloDotprompt = defineDotprompt(
  {
    name: 'helloPrompt',
    model: 'googleai/gemini-1.5-flash-latest',
    input: {
      schema: z.object({ name: z.string() }),
    },
  },
  `You are a helpful AI assistant named Walt. Say hello to {{name}}`
);

defineFlow(
  {
    name: 'simpleDotprompt',
  },
  () => {
    return helloDotprompt.generate({ input: { name: 'Fred' } });
  }
);

const threeGreetingsPrompt = defineDotprompt(
  {
    name: 'threeGreetingsPrompt',
    model: 'googleai/gemini-1.5-flash-latest',
    input: {
      schema: z.object({ name: z.string() }),
    },
    output: {
      format: 'json',
      schema: z.object({
        short: z.string(),
        friendly: z.string(),
        likeAPirate: z.string(),
      }),
    },
  },
  `You are a helpful AI assistant named Walt. Say hello to {{name}}, write a response for each of the styles requested`
);

defineFlow(
  {
    name: 'threeGreetingsPrompt',
  },
  () => {
    return threeGreetingsPrompt.generate({ input: { name: 'Fred' } });
  }
);

// Start a flow server, which exposes your flows as HTTP endpoints. This call
// must come last, after all of your plug-in configuration and flow definitions.
// You can optionally specify a subset of flows to serve, and configure some
// HTTP server options, but by default, the flow server serves all defined flows.
startFlowsServer();
