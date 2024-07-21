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

import { generate } from '@genkit-ai/ai';
import {
  GenerateResponseChunkSchema,
  MessageData,
  ModelReference,
  Part,
} from '@genkit-ai/ai/model';
import { StreamingCallback, configureGenkit } from '@genkit-ai/core';
import { defineFlow, run, startFlowsServer } from '@genkit-ai/flow';
import { gemini15Flash, llama3, vertexAI, VertexAIEvaluationMetricType } from '@genkit-ai/vertexai';
import { inMemoryStore } from './memory.js';

import { GenerateResponseChunk } from '@genkit-ai/ai/lib/generate.js';
import { PartSchema } from '@genkit-ai/ai/model';
import { z } from 'zod';

export const AgentInput = z.object({
  commentaryMode: z.enum(['normal', 'tutor', 'translator']),
  conversationId: z.string(),
  prompt: z.union([z.string(), PartSchema, z.array(PartSchema)]),
  config: z.record(z.string(), z.any()).optional(),
  llmIndex: z.number(),
});

const commentaryPrompts: Record<string, string> = {
  normal: "You are a critic. Check the last messsage for errors or bugs. Be polite. If no obvious errors just make a short complement, for example: Great job, I don't see any bugs.",
  tutor: "You are tutor. Explain the previous response.",
  translator: "You are a French translator. Translate eveything.",
}

configureGenkit({
  plugins: [
    vertexAI({
      location: 'us-central1',
      modelGardenModels: [llama3],
      evaluation: {
        metrics: [VertexAIEvaluationMetricType.SAFETY, VertexAIEvaluationMetricType.FLUENCY]
      }
    }),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

const ChatbotStreamChunkSchema = GenerateResponseChunkSchema.extend({
  llmIndex: z.number(),
});
type ChatbotStreamChunk = z.infer<typeof ChatbotStreamChunkSchema>;

const historyStore = inMemoryStore();

const llms: ModelReference<any>[] = [llama3, llama3];

export const chatbotFlow = defineFlow(
  {
    name: 'chatbotFlow',
    inputSchema: AgentInput,
    outputSchema: z.string(),
    streamSchema: ChatbotStreamChunkSchema,
  },
  async (request, streamingCallback) => {
    // Retrieve conversation history.
    const history = await run(
      'retrieve-history',
      request.conversationId,
      async () => {
        return (await historyStore?.load(request.conversationId)) || [];
      }
    );
    
    // Run the user prompt (with history) through the primary LLM.
    const mainResp = await generate({
      prompt: request.prompt,
      history: addSystemPrompt('You are a helpful agent.', history),
      model: llms[request.llmIndex],
      streamingCallback: addLlmIndex(request.llmIndex, streamingCallback),
    });
    let responseText = mainResp.text();

    // Run the user prompt and primary LLM output through the commentator LLM.
    const commentaryLlmIdx = (request.llmIndex + 1) % llms.length;
    const commentaryResp = await generate({
      prompt: [
        ...toParts(request.prompt),
        ...mainResp.candidates[0].message.content,
      ],
      history: addSystemPrompt(
        commentaryPrompts[request.commentaryMode],
        history
      ),
      model: llms[commentaryLlmIdx],
      streamingCallback: addLlmIndex(commentaryLlmIdx, streamingCallback),
    });
    responseText += '\n\n' + commentaryResp.text();

    // Save history.
    const historyToSave = stripSystemPrompt(commentaryResp.toHistory());
    await run(
      'save-history',
      {
        conversationId: request.conversationId,
        history: historyToSave,
      },
      async () => {
        await historyStore?.save(request.conversationId, historyToSave);
      }
    );
    return responseText;
  }
);

function toParts(input: string | Part | Part[]): Part[] {
  if (typeof input === 'string') {
    return [
      {
        text: input,
      },
    ];
  }
  if (Array.isArray(input)) {
    return input;
  }
  return [input];
}

function stripSystemPrompt(history: MessageData[]): MessageData[] {
  return history.filter((h) => h.role !== 'system');
}

function addSystemPrompt(
  prompt: string,
  history: MessageData[]
): MessageData[] {
  return [
    {
      role: 'system',
      content: [
        {
          text: prompt,
        },
      ],
    },
    ...history,
  ];
}

function addLlmIndex(
  idx: number,
  streamingCallback: StreamingCallback<ChatbotStreamChunk> | undefined
): undefined | ((chunk: GenerateResponseChunk) => void) {
  if (!streamingCallback) {
    return undefined;
  }
  return (chunk: GenerateResponseChunk): void => {
    streamingCallback({
      llmIndex: idx,
      ...chunk.toJSON(),
    });
  };
}

startFlowsServer();
