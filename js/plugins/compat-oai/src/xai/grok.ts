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

import { ModelInfo, modelRef, ModelReference } from 'genkit/model';
import { ChatCompletionCommonConfigSchema } from '../model';

/**
 * Language models that support text -> text, tool calling, structured output
 */
const XAI_LANGUGAGE_MODEL_INFO: ModelInfo = {
  supports: {
    multiturn: true,
    tools: true,
    media: false,
    systemRole: true,
    output: ['text', 'json'],
  },
};

function commonRef(
  name: string,
  info?: ModelInfo
): ModelReference<typeof ChatCompletionCommonConfigSchema> {
  return modelRef({
    name,
    configSchema: ChatCompletionCommonConfigSchema,
    info: info ?? XAI_LANGUGAGE_MODEL_INFO,
  });
}

const grok3 = commonRef('xai/grok-3');

const grok3Fast = commonRef('xai/grok-3-fast');

const grok3Mini = commonRef('xai/grok-3-mini');

const grok3MiniFast = commonRef('xai/grok-3-mini-fast');

const grok2Vision1212 = commonRef('xai/grok-2-vision-1212', {
  supports: {
    multiturn: false,
    tools: true,
    media: true,
    systemRole: false,
    output: ['text', 'json'],
  },
});

export const SUPPORTED_LANGUAGE_MODELS = {
  'grok-3': grok3,
  'grok-3-fast': grok3Fast,
  'grok-3-mini': grok3Mini,
  'grok-3-mini-fast': grok3MiniFast,
  'grok-2-vision-1212': grok2Vision1212,
};
