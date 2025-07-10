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

const deepseekChat = modelRef({
  name: 'deepseek/deepseek-chat',
  info: {
    label: 'DeepSeek - DeepSeek Chat',
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

const deepseekReasoner = modelRef({
  name: 'deepseek/deepseek-reasoner',
  info: {
    label: 'DeepSeek - DeepSeek Reasoner',
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

export const SUPPORTED_DEEPSEEK_MODELS = {
  'deepseek-reasoner': deepseekReasoner,
  'deepseek-chat': deepseekChat,
};
