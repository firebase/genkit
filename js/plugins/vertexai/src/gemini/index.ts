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

import { ModelAction, ModelReference } from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from '..';

let SUPPORTED_GEMINI_MODELS: Record<string, { name: string }> = {};
let geminiModel;

let gemini15Flash: ModelReference<any>;
let gemini15FlashPreview: ModelReference<any>;
let gemini15Pro: ModelReference<any>;
let gemini15ProPreview: ModelReference<any>;
let geminiPro: ModelReference<any>;
let geminiProVision: ModelReference<any>;

export default async function vertexAiGemini(
  projectId: string,
  location: string,
  options: PluginOptions | undefined,
  authClient: GoogleAuth,
  vertexClientFactory: any
): Promise<ModelAction<any>[]> {
  await initalizeDependencies();

  const geminiModels = Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
    geminiModel(name, vertexClientFactory, { projectId, location })
  );

  return geminiModels;
}

async function initalizeDependencies() {
  const {
    gemini15Flash: gemini15FlashImport,
    gemini15FlashPreview: gemini15FlashPreviewImport,
    gemini15Pro: gemini15ProImport,
    gemini15ProPreview: gemini15ProPreviewImport,
    geminiModel: geminiModelImport,
    geminiPro: geminiProImport,
    geminiProVision: geminiProVisionImport,
    SUPPORTED_GEMINI_MODELS: SUPPORTED_GEMINI_MODELS_IMPORT,
  } = await import('./gemini.js');

  gemini15Flash = gemini15FlashImport;
  gemini15FlashPreview = gemini15FlashPreviewImport;
  gemini15Pro = gemini15ProImport;
  gemini15ProPreview = gemini15ProPreviewImport;
  geminiModel = geminiModelImport;
  geminiPro = geminiProImport;
  geminiProVision = geminiProVisionImport;
  SUPPORTED_GEMINI_MODELS = SUPPORTED_GEMINI_MODELS_IMPORT;
}

export {
  gemini15Flash,
  gemini15FlashPreview,
  gemini15Pro,
  gemini15ProPreview,
  geminiPro,
  geminiProVision,
};
