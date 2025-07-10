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

export const SUPPORTED_LANGUAGE_MODELS = {
  'grok-3': commonRef('xai/grok-3'),
  'grok-3-fast': commonRef('xai/grok-3-fast'),
  'grok-3-mini': commonRef('xai/grok-3-mini'),
  'grok-3-mini-fast': commonRef('xai/grok-3-mini-fast'),
  'grok-2-vision-1212': commonRef('xai/grok-2-vision-1212', {
    supports: {
      multiturn: false,
      tools: true,
      media: true,
      systemRole: false,
      output: ['text', 'json'],
    },
  }),
};
