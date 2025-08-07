/**
 * Copyright 2025 Google LLC
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

import { claude } from './ai-tools/claude';
import { gemini } from './ai-tools/gemini';
import { generic } from './ai-tools/generic';
import { AIToolModule } from './types';

export const AI_TOOLS: Record<string, AIToolModule> = {
  gemini,
  claude,
  generic,
};
