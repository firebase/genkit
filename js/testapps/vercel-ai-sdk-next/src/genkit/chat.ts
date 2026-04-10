/**
 * Copyright 2025 Google LLC
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

import {
  FlowOutputSchema,
  MessagesSchema,
  StreamChunkSchema,
  toFlowOutput,
  toStreamChunks,
} from '@genkit-ai/vercel-ai-sdk';
import { z, type MessageData } from 'genkit';
import { ai } from './index';

/**
 * A toy weather tool that the model can call.  The result is fed back to the
 * model automatically by Genkit's multi-step generate loop, exercising the
 * tool-request → tool-result path through toStreamChunks().
 */
const getWeather = ai.defineTool(
  {
    name: 'getWeather',
    description: 'Get the current weather conditions for a city.',
    inputSchema: z.object({ city: z.string().describe('City name') }),
    outputSchema: z.object({
      temperatureC: z.number(),
      condition: z.string(),
    }),
  },
  async ({ city }) => {
    // Simulated — replace with a real API call as needed.
    const conditions = ['sunny', 'cloudy', 'rainy', 'windy'];
    return {
      temperatureC: 15 + Math.floor(Math.abs(city.charCodeAt(0)) % 20),
      condition: conditions[city.charCodeAt(0) % conditions.length],
    };
  }
);

/**
 * Chat flow for use with chatHandler + useChat.
 *
 * inputSchema:  MessagesSchema    — receives the full conversation history
 *               (already converted from UIMessage[] by chatHandler).
 * streamSchema: StreamChunkSchema — drives the full useChat protocol
 *               (text, reasoning, tools, citations, step markers, etc.).
 * outputSchema: FlowOutputSchema  — populates finish event with
 *               finishReason and token usage.
 *
 * Demonstrates:
 * - toStreamChunks() for text, reasoning, and tool-request/tool-result chunks
 * - A custom `data` chunk carrying model metadata on every response
 */
export const chatFlow = ai.defineFlow(
  {
    name: 'chat',
    inputSchema: MessagesSchema,
    outputSchema: FlowOutputSchema,
    streamSchema: StreamChunkSchema,
  },
  async (input, { sendChunk }) => {
    const { stream, response } = ai.generateStream({
      system:
        'You are a helpful assistant. Be concise. ' +
        'You have access to a getWeather tool — use it when weather is mentioned.',
      messages: input.messages as MessageData[],
      tools: [getWeather],
    });

    for await (const chunk of stream) {
      for (const c of toStreamChunks(chunk)) {
        sendChunk(c);
      }
    }

    const res = await response;

    // Emit a custom data chunk with usage metadata so the client can display it.
    if (res.usage) {
      sendChunk({
        type: 'data',
        id: 'usage',
        value: res.usage,
      });
    }

    return toFlowOutput(res);
  }
);
