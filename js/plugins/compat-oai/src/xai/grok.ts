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

import { modelRef } from 'genkit/model';
import { ChatCompletionCommonConfigSchema } from '../model';

const grok3 = modelRef({
  name: 'xai/grok-3',
  info: {
    label: 'xAI - Grok 3',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: ChatCompletionCommonConfigSchema,
});

const grok3Fast = modelRef({
  name: 'xai/grok-3-fast',
  info: {
    label: 'xAI - Grok 3 Fast',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: ChatCompletionCommonConfigSchema,
});

const grok3Mini = modelRef({
  name: 'xai/grok-3-mini',
  info: {
    label: 'xAI - Grok 3 Mini',
    supports: {
      multiturn: true,
      tools: true,
      systemRole: true,
      media: false,
      output: ['text', 'json'],
    },
  },
  configSchema: ChatCompletionCommonConfigSchema,
});

export const grok3MiniFast = modelRef({
  name: 'xai/grok-3-mini-fast',
  info: {
    label: 'xAI - Grok 3 Fast',
    supports: {
      multiturn: true,
      tools: true,
      systemRole: true,
      media: false,
      output: ['text', 'json'],
    },
  },
  configSchema: ChatCompletionCommonConfigSchema,
});

export const grok2Vision1212 = modelRef({
  name: 'xai/grok-2-vision-1212',
  info: {
    label: 'xAI - Grok 2 Vision 1212',
    supports: {
      multiturn: false,
      tools: true,
      systemRole: false,
      media: true,
      output: ['text', 'json'],
    },
  },
  configSchema: ChatCompletionCommonConfigSchema,
});

export const SUPPORTED_LANGUAGE_MODELS = {
  'grok-3': grok3,
  'grok-3-fast': grok3Fast,
  'grok-3-mini': grok3Mini,
  'grok-3-mini-fast': grok3MiniFast,
  'grok-2-vision-1212': grok2Vision1212,
};
