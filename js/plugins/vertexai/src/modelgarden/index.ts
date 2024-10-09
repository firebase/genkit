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

import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from '../index.js';
import { ModelAction, ModelReference } from 'genkit/model';

let modelGardenOpenaiCompatibleModel;
let SUPPORTED_OPENAI_FORMAT_MODELS: Record<string, { name: string }> = {};
let anthropicModel;
let SUPPORTED_ANTHROPIC_MODELS: Record<string, { name: string }> = {};

let llama3: ModelReference<any> | undefined;
let llama31:  ModelReference<any> | undefined;
let llama32: ModelReference<any> | undefined;
let claude35Sonnet: ModelReference<any> | undefined;
let claude3Haiku: ModelReference<any> | undefined;
let claude3Opus: ModelReference<any> | undefined;
let claude3Sonnet: ModelReference<any> | undefined;

export default async function vertexAiModelGarden(
    projectId: string,
    location: string,
    options: PluginOptions | undefined,
    authClient: GoogleAuth,
): Promise<ModelAction<any>[]> {
    await initalizeDependencies();

    const models: ModelAction<any>[] = [];
    const mgModels = options?.modelGardenModels || options?.modelGarden?.models;
    mgModels!.forEach((m) => {
      const anthropicEntry = Object.entries(SUPPORTED_ANTHROPIC_MODELS).find(
        ([_, value]) => value.name === m.name
      );
      if (anthropicEntry) {
        models.push(anthropicModel(anthropicEntry[0], projectId, location));
        return;
      }
      const openaiModel = Object.entries(SUPPORTED_OPENAI_FORMAT_MODELS).find(
        ([_, value]) => value.name === m.name
      );
      if (openaiModel) {
        models.push(
          modelGardenOpenaiCompatibleModel(
            openaiModel[0],
            projectId,
            location,
            authClient,
            options?.modelGarden?.openAiBaseUrlTemplate
          )
        );
        return;
      }
      throw new Error(`Unsupported model garden model: ${m.name}`);
    });
    return models;
}

async function initalizeDependencies() {
  const {
    llama3: llama3import,
    llama31: llama31import,
    llama32: llama32import,
    modelGardenOpenaiCompatibleModel: modelGardenOpenaiCompatibleModelImport,
    SUPPORTED_OPENAI_FORMAT_MODELS: SUPPORTED_OPENAI_FORMAT_MODELS_IMPORT,
  } = await import('./model_garden.js');

  const {
    anthropicModel: anthropicModelImport,
    claude35Sonnet: claude35SonnetImport,
    claude3Haiku: claude3HaikuImport,
    claude3Opus: claude3OpusImport,
    claude3Sonnet: claude3SonnetImport,
    SUPPORTED_ANTHROPIC_MODELS: SUPPORTED_ANTHROPIC_MODELS_IMPORT,
  } = await import('./anthropic.js');

  modelGardenOpenaiCompatibleModel = modelGardenOpenaiCompatibleModelImport;
  SUPPORTED_OPENAI_FORMAT_MODELS = SUPPORTED_OPENAI_FORMAT_MODELS_IMPORT;
  anthropicModel = anthropicModelImport;
  SUPPORTED_ANTHROPIC_MODELS = SUPPORTED_ANTHROPIC_MODELS_IMPORT

  // llama3Export = llama3;
  llama3 = llama3import;
  llama31 = llama31import;
  llama32 = llama32import;
  claude35Sonnet = claude35SonnetImport;
  claude3Haiku = claude3HaikuImport;
  claude3Opus = claude3OpusImport;
  claude3Sonnet = claude3SonnetImport;
}

export {
  llama3,
  llama31,
  llama32,
  claude35Sonnet,
  claude3Haiku,
  claude3Opus,
  claude3Sonnet
}
