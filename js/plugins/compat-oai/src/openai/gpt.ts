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

const gpt45 = commonRef('openai/gpt-4.5');
const gpt45Preview = commonRef('openai/gpt-4.5-preview');

const gpt4o = commonRef('openai/gpt-4o');
const gpt4o20240513 = commonRef('openai/gpt-4o-2024-05-13');

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

const gpt4oMini = commonRef('openai/gpt-4o-mini');
const gpt4oMini20240718 = commonRef('openai/gpt-4o-mini-2024-07-18');

const gpt4Turbo = commonRef('openai/gpt-4-turbo');
const gpt4Turbo20240409 = commonRef('openai/gpt-4-turbo-2024-04-09');
const gpt4TurboPreview = commonRef('openai/gpt-4-turbo-preview');
const gpt40125Preview = commonRef('openai/gpt-4-0125-preview');
const gpt41106Preview = commonRef('openai/gpt-4-1106-preview');

const GPT_4_VISION_MODEL_INFO: ModelInfo = {
  supports: {
    multiturn: true,
    tools: false,
    media: true,
    systemRole: true,
    output: ['text'],
  },
};
const gpt4Vision = commonRef('openai/gpt-4-vision', GPT_4_VISION_MODEL_INFO);
const gpt4VisionPreview = commonRef(
  'openai/gpt-4-vision-preview',
  GPT_4_VISION_MODEL_INFO
);
const gpt41106VisionPreview = commonRef(
  'openai/gpt-4-1106-vision-preview',
  GPT_4_VISION_MODEL_INFO
);

const GPT_4_MODEL_INFO: ModelInfo = {
  supports: {
    multiturn: true,
    tools: true,
    media: false,
    systemRole: true,
    output: ['text'],
  },
};
const gpt4 = commonRef('openai/gpt-4', GPT_4_MODEL_INFO);
const gpt40613 = commonRef('openai/gpt-4-0613', GPT_4_MODEL_INFO);
const gpt432k = commonRef('openai/gpt-4-32k', GPT_4_MODEL_INFO);
const gpt432k0613 = commonRef('openai/gpt-4-32k-0613', GPT_4_MODEL_INFO);

const GPT_35_MODEL_INFO: ModelInfo = {
  supports: {
    multiturn: true,
    tools: true,
    media: false,
    systemRole: true,
    output: ['text', 'json'],
  },
};
const gpt35Turbo = commonRef('openai/gpt-3.5-turbo', GPT_35_MODEL_INFO);
const gpt35Turbo0125 = commonRef(
  'openai/gpt-3.5-turbo-0125',
  GPT_35_MODEL_INFO
);
const gpt35Turbo1106 = commonRef(
  'openai/gpt-3.5-turbo-1106',
  GPT_35_MODEL_INFO
);

const ALL_GPT_MODELS = [
  gpt45,
  gpt45Preview,
  gpt4o,
  gpt4o20240513,
  o1,
  o3,
  o3Mini,
  o4Mini,
  gpt4oMini,
  gpt4oMini20240718,
  gpt4Turbo,
  gpt4Turbo20240409,
  gpt4TurboPreview,
  gpt40125Preview,
  gpt41106Preview,
  gpt4Vision,
  gpt4VisionPreview,
  gpt41106VisionPreview,
  gpt4,
  gpt40613,
  gpt432k,
  gpt432k0613,
  gpt35Turbo,
  gpt35Turbo0125,
  gpt35Turbo1106,
];

export const SUPPORTED_GPT_MODELS = Object.fromEntries(
  ALL_GPT_MODELS.map((ref) => [ref.name.split('openai/')[1], ref])
);
