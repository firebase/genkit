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
  toStreamChunks,
} from '@genkit-ai/vercel-ai-sdk';
import type { MessageData } from 'genkit';
import { ai } from './index';

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
 * toStreamChunks() converts each GenerateResponseChunk to the appropriate
 * StreamChunk values (text, reasoning, tool-request) automatically.
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
      system: 'You are a helpful assistant. Be concise.',
      messages: input.messages as MessageData[],
    });

    for await (const chunk of stream) {
      for (const c of toStreamChunks(chunk)) {
        sendChunk(c);
      }
    }

    const res = await response;
    return {
      finishReason: res.finishReason,
      usage: res.usage as Record<string, unknown> | undefined,
    };
  }
);
