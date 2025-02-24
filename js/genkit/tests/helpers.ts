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

import { MessageData } from '@genkit-ai/ai';
import { BaseEvalDataPoint } from '@genkit-ai/ai/evaluator';
import { ModelAction, ModelInfo } from '@genkit-ai/ai/model';
import { SessionData, SessionStore } from '@genkit-ai/ai/session';
import { StreamingCallback } from '@genkit-ai/core';
import { Genkit } from '../src/genkit';
import {
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseData,
} from '../src/model';

export function defineEchoModel(
  ai: Genkit,
  modelInfo?: ModelInfo
): ModelAction {
  const model = ai.defineModel(
    {
      name: 'echoModel',
      ...modelInfo,
    },
    async (request, sendChunk) => {
      (model as any).__test__lastRequest = request;
      (model as any).__test__lastStreamingCallback = sendChunk;
      if (sendChunk) {
        await runAsync(() => {
          sendChunk({
            content: [
              {
                text: '3',
              },
            ],
          });
        });
        await runAsync(() => {
          sendChunk({
            content: [
              {
                text: '2',
              },
            ],
          });
        });
        await runAsync(() => {
          sendChunk({
            content: [
              {
                text: '1',
              },
            ],
          });
        });
      }
      return await runAsync(() => ({
        message: {
          role: 'model',
          content: [
            {
              text:
                'Echo: ' +
                request.messages
                  .map(
                    (m) =>
                      (m.role === 'user' || m.role === 'model'
                        ? ''
                        : `${m.role}: `) + m.content.map((c) => c.text).join()
                  )
                  .join(),
            },
            {
              text: '; config: ' + JSON.stringify(request.config),
            },
          ],
        },
        finishReason: 'stop',
      }));
    }
  );
  return model;
}

export function bonknessEvaluator(ai: Genkit) {
  return ai.defineEvaluator(
    {
      name: 'bonkness',
      displayName: 'Bonkness',
      definition: 'Judges whether a statement is bonk',
    },
    async (datapoint: BaseEvalDataPoint) => {
      return {
        testCaseId: datapoint.testCaseId,
        evaluation: {
          score: 'Much bonk',
          details: {
            reasoning: 'Because I said so!',
          },
        },
      };
    }
  );
}

export async function runAsync<O>(fn: () => O): Promise<O> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(fn()), 0);
  });
}

export class TestMemorySessionStore<S> implements SessionStore<S> {
  private data: Record<string, SessionData<S>> = {};

  async get(sessionId: string): Promise<SessionData<S> | undefined> {
    return this.data[sessionId];
  }

  async save(sessionId: string, sessionData: SessionData<S>): Promise<void> {
    this.data[sessionId] = sessionData;
  }
}
export function defineStaticResponseModel(
  ai: Genkit,
  message: MessageData
): ModelAction {
  return ai.defineModel(
    {
      name: 'staticResponseModel',
    },
    async () => {
      return await runAsync(() => ({
        message,
      }));
    }
  );
}

export type ProgrammableModel = ModelAction & {
  handleResponse: (
    req: GenerateRequest,
    sendChunk?: StreamingCallback<GenerateResponseChunkData>
  ) => Promise<GenerateResponseData>;

  lastRequest?: GenerateRequest;
};

export function defineProgrammableModel(ai: Genkit): ProgrammableModel {
  const pm = ai.defineModel(
    {
      name: 'programmableModel',
      supports: {
        tools: true,
      },
    },
    async (request, sendChunk) => {
      pm.lastRequest = JSON.parse(JSON.stringify(request));
      return pm.handleResponse(request, sendChunk);
    }
  ) as ProgrammableModel;

  return pm;
}
