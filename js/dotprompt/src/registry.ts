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

import { config } from '@genkit-ai/common/config';
import { logger } from '@genkit-ai/common/logging';
import { lookupAction, registerAction } from '@genkit-ai/common/registry';
import { readFileSync } from 'fs';
import { join } from 'path';
import { Prompt, PromptAction } from './prompt';

export async function lookupPrompt(
  name: string,
  variant?: string
): Promise<Prompt> {
  const registryPrompt = (await lookupAction(
    `/prompt/${name}${variant ? `.${variant}` : ''}`
  )) as PromptAction;
  if (registryPrompt) return Prompt.fromAction(registryPrompt);

  const prompt = loadPrompt(name, variant);
  registerAction(
    'prompt',
    `/prompt/${name}${variant ? `.${variant}` : ''}`,
    prompt.action()
  );
  return prompt;
}

function loadPrompt(name: string, variant?: string) {
  const dir = config.options.promptDir || './prompts';
  try {
    const source = readFileSync(
      join(dir, `${name}${variant ? `.${variant}` : ''}.prompt`),
      'utf8'
    );
    const prompt = Prompt.parse(name, source);
    prompt.variant = variant;
    return prompt;
  } catch (e) {
    if (variant) {
      logger.warn(
        `Prompt '${name}.${variant}' not found, trying '${name}' without variant.`
      );
      return loadPrompt(name);
    }
    throw new Error(`Prompt ${name}${variant ? `.${variant}` : ''} not found`);
  }
}
