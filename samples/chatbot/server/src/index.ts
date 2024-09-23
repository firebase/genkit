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
  ModelReference,
  PartSchema,
} from '@genkit-ai/ai/model';
import { genkit, run } from '@genkit-ai/core';
import {
  VertexAIEvaluationMetricType,
  gemini15Flash,
  llama3,
  vertexAI,
} from '@genkit-ai/vertexai';
import { z } from 'zod';
import { inMemoryStore } from './memory.js';

export const AgentInput = z.object({
  conversationId: z.string(),
  prompt: z.union([z.string(), PartSchema, z.array(PartSchema)]),
  config: z.record(z.string(), z.any()).optional(),
  llmIndex: z.number(),
});

const ai = genkit({
  plugins: [
    vertexAI({
      location: 'us-central1',
      modelGardenModels: [llama3],
      evaluation: {
        metrics: [
          VertexAIEvaluationMetricType.SAFETY,
          VertexAIEvaluationMetricType.FLUENCY,
        ],
      },
    }),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

const llms: ModelReference<any>[] = [gemini15Flash, llama3];

const historyStore = inMemoryStore();

export const chatbotFlow = ai.defineStreamingFlow(
  {
    name: 'chatbotFlow',
    inputSchema: AgentInput,
    outputSchema: z.string(),
    streamSchema: GenerateResponseChunkSchema,
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
      history: history,
      model: llms[request.llmIndex],
      streamingCallback,
    });

    // Save history.
    await run(
      'save-history',
      {
        conversationId: request.conversationId,
        history: mainResp.toHistory(),
      },
      async () => {
        await historyStore?.save(request.conversationId, mainResp.toHistory());
      }
    );
    return mainResp.text();
  }
);
