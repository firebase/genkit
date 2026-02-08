/**
 * Copyright 2026 Google LLC
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

import { BaseGenkitPluginV2 } from '@genkit-ai/core';
import { GenerateMiddleware } from './generate/middleware.js';
import { ModelAction } from './model.js';

export interface GenkitPluginV2 extends BaseGenkitPluginV2 {
  // Returns a list of generate middleware to be used in `generate({use: [...])`.
  generateMiddleware?: () => GenerateMiddleware<any>[];

  // A shortcut for resolving a model.
  model(name: string): Promise<ModelAction>;
}
