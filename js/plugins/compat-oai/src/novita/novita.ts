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

import { ModelInfo, ModelReference } from 'genkit/model';
import {
  ChatCompletionCommonConfigSchema,
  compatOaiModelRef,
} from '../model';

/** Novita ModelRef helper, with Novita-specific config. */
export function novitaModelRef(params: {
  name: string;
  info?: ModelInfo;
  config?: any;
}): ModelReference<typeof ChatCompletionCommonConfigSchema> {
  return compatOaiModelRef({
    ...params,
    configSchema: ChatCompletionCommonConfigSchema,
    info: params.info ?? {
      supports: {
        multiturn: true,
        tools: true,
        media: false,
        systemRole: true,
        output: ['text', 'json'],
        constrained: 'all',
      },
    },
    namespace: 'novita',
  });
}

export const SUPPORTED_NOVITA_MODELS = {
  'moonshotai/kimi-k2.5': novitaModelRef({
    name: 'moonshotai/kimi-k2.5',
    info: {
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
        constrained: 'all',
      },
    },
  }),
  'zai-org/glm-5': novitaModelRef({ name: 'zai-org/glm-5' }),
  'minimax/minimax-m2.5': novitaModelRef({ name: 'minimax/minimax-m2.5' }),
};
