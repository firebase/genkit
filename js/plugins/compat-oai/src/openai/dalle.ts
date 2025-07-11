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
import { modelRef } from 'genkit/model';
import {
  IMAGE_GENERATION_MODEL_INFO,
  ImageGenerationCommonConfigSchema,
} from '../image';

export const dallE3 = modelRef({
  name: 'openai/dall-e-3',
  info: {
    label: 'OpenAI - DALL-E 3',
    ...IMAGE_GENERATION_MODEL_INFO,
  },
  configSchema: ImageGenerationCommonConfigSchema,
});

export const SUPPORTED_IMAGE_MODELS = {
  'dall-e-3': dallE3,
};
