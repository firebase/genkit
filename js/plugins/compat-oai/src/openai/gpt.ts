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

import type { Genkit, ModelReference } from 'genkit';
import type { ModelAction, ModelInfo } from 'genkit/model';
import { modelRef } from 'genkit/model';
import type OpenAI from 'openai';
import { OpenAiConfigSchema, textModel } from '../model';

export const gpt45 = modelRef({
  name: 'openai/gpt-4.5',
  info: {
    versions: ['gpt-4.5-preview'],
    label: 'OpenAI - GPT-4.5',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt4o = modelRef({
  name: 'openai/gpt-4o',
  info: {
    versions: ['gpt-4o', 'gpt-4o-2024-05-13'],
    label: 'OpenAI - GPT-4o',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const o1Preview = modelRef({
  name: 'openai/o1-preview',
  info: {
    versions: ['o1-preview'],
    label: 'OpenAI - o1 Preview',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const o1Mini = modelRef({
  name: 'openai/o1',
  info: {
    versions: ['o1-mini'],
    label: 'OpenAI - o1 Mini',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const o1 = modelRef({
  name: 'openai/o1',
  info: {
    versions: ['o1'],
    label: 'OpenAI - o1',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const o3 = modelRef({
  name: 'openai/o3',
  info: {
    versions: ['o3'],
    label: 'OpenAI - o3',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const o3Mini = modelRef({
  name: 'openai/o3-mini',
  info: {
    versions: ['o3-mini'],
    label: 'OpenAI - o3 Mini',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const o4Mini = modelRef({
  name: 'openai/o4-mini',
  info: {
    versions: ['o4-mini'],
    label: 'OpenAI - o4 Mini',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt4oMini = modelRef({
  name: 'openai/gpt-4o-mini',
  info: {
    versions: ['gpt-4o-mini', 'gpt-4o-mini-2024-07-18'],
    label: 'OpenAI - GPT-4o mini',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt4Turbo = modelRef({
  name: 'openai/gpt-4-turbo',
  info: {
    versions: [
      'gpt-4-turbo',
      'gpt-4-turbo-2024-04-09',
      'gpt-4-turbo-preview',
      'gpt-4-0125-preview',
      'gpt-4-1106-preview',
    ],
    label: 'OpenAI - GPT-4 Turbo',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt4Vision = modelRef({
  name: 'openai/gpt-4-vision',
  info: {
    versions: ['gpt-4-vision-preview', 'gpt-4-1106-vision-preview'],
    label: 'OpenAI - GPT-4 Vision',
    supports: {
      multiturn: true,
      tools: false,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt4 = modelRef({
  name: 'openai/gpt-4',
  info: {
    versions: ['gpt-4', 'gpt-4-0613', 'gpt-4-32k', 'gpt-4-32k-0613'],
    label: 'OpenAI - GPT-4',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt41 = modelRef({
  name: 'openai/gpt-4.1',
  info: {
    versions: ['gpt-4.1'],
    label: 'OpenAI - GPT-4.1',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt41Mini = modelRef({
  name: 'openai/gpt-4.1-mini',
  info: {
    versions: ['gpt-4.1-mini'],
    label: 'OpenAI - GPT-4.1 Mini',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt41Nano = modelRef({
  name: 'openai/gpt-4.1-nano',
  info: {
    versions: ['gpt-4.1-nano'],
    label: 'OpenAI - GPT-4.1 Nano',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const gpt35Turbo = modelRef({
  name: 'openai/gpt-3.5-turbo',
  info: {
    versions: ['gpt-3.5-turbo-0125', 'gpt-3.5-turbo', 'gpt-3.5-turbo-1106'],
    label: 'OpenAI - GPT-3.5 Turbo',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['json', 'text'],
    },
  },
  configSchema: OpenAiConfigSchema,
});

export const SUPPORTED_GPT_MODELS: Record<
  string,
  ModelReference<typeof OpenAiConfigSchema>
> = {
  'gpt-4.5': gpt45,
  'gpt-4o': gpt4o,
  'gpt-4o-mini': gpt4oMini,
  'gpt-4-turbo': gpt4Turbo,
  'gpt-4-vision': gpt4Vision,
  'gpt-4': gpt4,
  'gpt-4.1': gpt41,
  'gpt-4.1-mini': gpt41Mini,
  'gpt-4.1-nano': gpt41Nano,
  'gpt-3.5-turbo': gpt35Turbo,
  'o1-preview': o1Preview,
  o1: o1,
  'o1-mini': o1Mini,
  o3: o3,
  'o3-mini': o3Mini,
  'o4-mini': o4Mini,
};

/**
 * Defines a GPT model with the given name and OpenAI client.
 * @param name The name of the GPT model.
 * @param client The OpenAI client instance.
 * @returns The defined GPT model.
 * @throws An error if the specified model is not supported.
 */
export function gptModel(
  ai: Genkit,
  name: string,
  client: OpenAI,
  modelInfo?: ModelInfo,
  modelConfig?: any
): ModelAction<typeof OpenAiConfigSchema> {
  const modelId = `openai/${name}`;
  const model = SUPPORTED_GPT_MODELS[name];
  if (!model) {
    SUPPORTED_GPT_MODELS[name] = modelRef({
      name: modelId,
      info: modelInfo,
      configSchema: modelConfig?.configSchema,
    });
  }

  return textModel(ai, modelId, client, model);
}
