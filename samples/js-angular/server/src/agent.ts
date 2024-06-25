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

import { GenerateResponse, generate } from '@genkit-ai/ai';
import {
  GenerateResponseSchema,
  MessageData,
  ModelArgument,
  PartSchema,
} from '@genkit-ai/ai/model';
import { ToolArgument } from '@genkit-ai/ai/tool';
import { defineFlow, run } from '@genkit-ai/flow';
import { z } from 'zod';

export interface HistoryStore {
  load(id: string): Promise<MessageData[] | undefined>;
  save(id: string, history: MessageData[]): Promise<void>;
}

export const AgentInput = z.object({
  conversationId: z.string(),
  prompt: z.union([z.string(), PartSchema, z.array(PartSchema)]),
  config: z.record(z.string(), z.any()).optional(),
});

type AgentFn = (
  request: z.infer<typeof AgentInput>,
  history: MessageData[] | undefined
) => Promise<GenerateResponse<any>>;

export function defineAgent(
  {
    name,
    tools,
    model,
    historyStore,
    systemPrompt,
    returnToolRequests,
  }: {
    name: string;
    systemPrompt?: string;
    tools?: ToolArgument[];
    model: ModelArgument<any>;
    historyStore?: HistoryStore;
    returnToolRequests?: boolean;
  },
  customFn?: AgentFn
) {
  return defineFlow(
    { name, inputSchema: AgentInput, outputSchema: GenerateResponseSchema },
    async (request, streamingCallback) => {
      const history = await run(
        'retrieve-history',
        request.conversationId,
        async () => {
          let history = request.conversationId
            ? await historyStore?.load(request.conversationId)
            : undefined;
          if (!history && systemPrompt) {
            history = [
              {
                role: 'system',
                content: [
                  {
                    text: systemPrompt,
                  },
                ],
              },
            ];
          }
          return history;
        }
      );
      const resp = customFn
        ? await customFn(request, history)
        : await generate({
            prompt: request.prompt,
            history,
            model,
            tools,
            returnToolRequests,
            streamingCallback,
          });
      await run(
        'save-history',
        { conversationId: request.conversationId, history: resp.toHistory() },
        async () => {
          request.conversationId
            ? await historyStore?.save(request.conversationId, resp.toHistory())
            : undefined;
        }
      );
      return resp.toJSON();
    }
  );
}
