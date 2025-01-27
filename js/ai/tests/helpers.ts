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

import { StreamingCallback } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import {
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseData,
  ModelAction,
  ModelInfo,
  defineModel,
} from '../src/model';

export async function runAsync<O>(fn: () => O): Promise<O> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(fn()), 0);
  });
}

export type ProgrammableModel = ModelAction & {
  handleResponse: (
    req: GenerateRequest,
    streamingCallback?: StreamingCallback<GenerateResponseChunkData>
  ) => Promise<GenerateResponseData>;

  lastRequest?: GenerateRequest;
};

export function defineProgrammableModel(
  registry: Registry,
  info?: ModelInfo
): ProgrammableModel {
  const pm = defineModel(
    registry,
    {
      ...info,
      name: 'programmableModel',
    },
    async (request, streamingCallback) => {
      pm.lastRequest = JSON.parse(JSON.stringify(request));
      return pm.handleResponse(request, streamingCallback);
    }
  ) as ProgrammableModel;

  return pm;
}
