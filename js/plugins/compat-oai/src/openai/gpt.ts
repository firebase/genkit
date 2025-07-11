/**
 * Copyright 2024 The Fire Company
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

const MULTIMODAL_MODEL_INFO: ModelInfo = {
  supports: {
    multiturn: true,
    tools: true,
    media: true,
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
    info: {
      ...MULTIMODAL_MODEL_INFO,
      ...(info ?? {}),
    },
  });
}

const gpt45 = commonRef('openai/gpt-4.5', {
  versions: ['gpt-4.5', 'gpt-4.5-preview'],
});

const gpt4o = commonRef('openai/gpt-4o', {
  versions: ['gpt-4o', 'gpt-4o-2024-05-13'],
});

const o1 = commonRef('openai/o1', {
  supports: {
    multiturn: true,
    tools: true,
    media: true,
    systemRole: false,
    output: ['text', 'json'],
  },
});

const o3 = commonRef('openai/o3', {
  supports: {
    multiturn: true,
    tools: true,
    media: true,
    systemRole: false,
    output: ['text', 'json'],
  },
});

const o3Mini = commonRef('openai/o3-mini', {
  supports: {
    multiturn: true,
    tools: true,
    media: false,
    systemRole: false,
    output: ['text', 'json'],
  },
});

const o4Mini = commonRef('openai/o4-mini', {
  supports: {
    multiturn: true,
    tools: true,
    media: true,
    systemRole: false,
    output: ['text', 'json'],
  },
});

const gpt4oMini = commonRef('openai/gpt-4o-mini', {
  versions: ['gpt-4o-mini', 'gpt-4o-mini-2024-07-18'],
});

const gpt4Turbo = commonRef('openai/gpt-4-turbo', {
  versions: [
    'gpt-4-turbo',
    'gpt-4-turbo-2024-04-09',
    'gpt-4-turbo-preview',
    'gpt-4-0125-preview',
    'gpt-4-1106-preview',
  ],
});

const gpt4Vision = commonRef('openai/gpt-4-vision', {
  versions: ['gpt-4-vision-preview', 'gpt-4-1106-vision-preview'],
  supports: {
    multiturn: true,
    tools: false,
    media: true,
    systemRole: true,
    output: ['text'],
  },
});

const gpt4 = commonRef('openai/gpt-4', {
  versions: ['gpt-4', 'gpt-4-0613', 'gpt-4-32k', 'gpt-4-32k-0613'],
  supports: {
    multiturn: true,
    tools: true,
    media: false,
    systemRole: true,
    output: ['text'],
  },
});

const gpt35Turbo = commonRef('openai/gpt-3.5-turbo', {
  versions: ['gpt-3.5-turbo-0125', 'gpt-3.5-turbo', 'gpt-3.5-turbo-1106'],
  supports: {
    multiturn: true,
    tools: true,
    media: false,
    systemRole: true,
    output: ['text', 'json'],
  },
});

export const SUPPORTED_GPT_MODELS = {
  // Multi-modal models
  'gpt-4.5': gpt45,
  'gpt-4o': gpt4o,
  'gpt-4o-mini': gpt4oMini,
  'gpt-4-turbo': gpt4Turbo,
  'gpt-4.1': commonRef('openai/gpt-4.1'),
  'gpt-4.1-mini': commonRef('openai/gpt-4.1-mini'),
  'gpt-4.1-nano': commonRef('openai/gpt-4.1-nano'),
  // Text-only multi-turn models
  'gpt-3.5-turbo': gpt35Turbo,
  'gpt-4': gpt4,
  o1: o1,
  o3: o3,
  'o3-mini': o3Mini,
  'o4-mini': o4Mini,
  'gpt-4-vision': gpt4Vision,
};
