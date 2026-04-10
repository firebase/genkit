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
  StreamChunkSchema,
  FlowOutputSchema,
  MessagesSchema,
} from '@genkit-ai/vercel-ai-sdk';
import type { MessageData } from 'genkit';
import { ai } from './index';

/**
 * Chat flow for use with chatHandler + useChat.
 *
 * inputSchema:  MessagesSchema  — receives the full conversation history
 *               (already converted from UIMessage[] by chatHandler).
 * streamSchema: StreamChunkSchema — drives the full useChat protocol
 *               (text, reasoning, tools, citations, step markers, etc.).
 * outputSchema: FlowOutputSchema — populates finish-message with
 *               finishReason and token usage.
 *
 * Because input.messages is in Genkit's native Part format (after the
 * chatHandler conversion), it can be passed directly to generateStream.
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
      // input.messages is in Genkit MessageData format — pass directly.
      messages: input.messages as MessageData[],
    });

    for await (const chunk of stream) {
      if (chunk.text) {
        sendChunk({ type: 'text', delta: chunk.text });
      }
      // Tool requests (if you add tools to the flow) would be forwarded like:
      // for (const tr of chunk.toolRequests ?? []) {
      //   sendChunk({ type: 'tool-request', toolCallId: tr.toolRequest.ref ?? '',
      //               toolName: tr.toolRequest.name, input: tr.toolRequest.input });
      // }
    }

    const res = await response;
    return {
      finishReason: res.finishReason,
      usage: res.usage as Record<string, number> | undefined,
    };
  }
);
