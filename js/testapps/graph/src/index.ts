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

import { configureGenkit } from '@genkit-ai/core';
import { vertexAI } from '@genkit-ai/vertexai';
import { defineEdge, defineFlow, graph } from 'genkitx-graph';
import * as z from 'zod';

configureGenkit({
  plugins: [
    vertexAI(),
    graph({
      port: 4003,
    }),
  ],
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});

export const addFlow = defineFlow(
  {
    name: 'addFlow',
    inputSchema: z.object({
      a: z.number(),
      b: z.number(),
    }),
    outputSchema: z.object({
      x: z.number(),
    }),
  },
  async ({ a, b }) => {
    return { x: a + b };
  }
);

export const subtractFlow = defineFlow(
  {
    name: 'subtractFlow',
    inputSchema: z.object({
      a: z.number(),
      b: z.number(),
    }),
    outputSchema: z.object({
      y: z.number(),
    }),
  },
  async ({ a, b }) => {
    return { y: a - b };
  }
);

export const multiplyFlow = defineFlow(
  {
    name: 'multiplyFlow',
    inputSchema: z.object({
      x: z.number(),
      y: z.number(),
    }),
    outputSchema: z.object({
      final: z.number(),
    }),
  },
  async ({ x, y }) => {
    return { final: x * y };
  }
);

defineEdge(addFlow, multiplyFlow, ['x']);

defineEdge(subtractFlow, multiplyFlow, ['y']);

// Now look at UI. Also the plugin is starting an express app (I was using the express app to interact with a flow diagram UI)
