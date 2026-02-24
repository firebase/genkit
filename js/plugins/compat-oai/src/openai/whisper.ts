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

import { z } from 'genkit';
import { ModelInfo } from 'genkit/model';
import { compatOaiWhisperModelRef } from '../audio';

/** OpenAI whisper ModelRef helper, same as the OpenAI-compatible spec. */
export function openAIWhisperModelRef<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(params: {
  name: string;
  info?: ModelInfo;
  configSchema?: CustomOptions;
  config?: any;
}) {
  return compatOaiWhisperModelRef({ ...params, namespace: 'openai' });
}

export const SUPPORTED_WHISPER_MODELS = {
  'whisper-1': openAIWhisperModelRef({
    name: 'whisper-1',
  }),
};
