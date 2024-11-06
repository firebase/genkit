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

import { Registry } from '@genkit-ai/core/registry';
import { readFileSync } from 'fs';
import { basename } from 'path';
import {
  defineDotprompt,
  Dotprompt,
  DotpromptRef,
  type PromptGenerateOptions,
} from './prompt.js';
import { loadPromptFolder, lookupPrompt } from './registry.js';

export { type PromptMetadata } from './metadata.js';
export { defineHelper, definePartial } from './template.js';
export {
  defineDotprompt,
  Dotprompt,
  loadPromptFolder,
  type PromptGenerateOptions,
};

export interface DotpromptPluginOptions {
  // Directory to look for .prompt files.
  //
  // Note: This directory will be searched recursively, and any sub-directory
  // paths will be included in the prompt name. E.g. - if a prompt file is
  // located at `<dir>/foo/bar.prompt`, the prompt name will be `foo-bar`.
  dir: string;
}

export async function prompt<Variables = unknown>(
  registry: Registry,
  name: string,
  options?: { variant?: string; dir?: string }
): Promise<Dotprompt<Variables>> {
  return (await lookupPrompt(
    registry,
    name,
    options?.variant,
    options?.dir ?? './prompts'
  )) as Dotprompt<Variables>;
}

export function promptRef<Variables = unknown>(
  name: string,
  options?: { variant?: string; dir?: string }
): DotpromptRef<Variables> {
  return new DotpromptRef(name, options);
}

export function loadPromptFile(registry: Registry, path: string): Dotprompt {
  return Dotprompt.parse(
    registry,
    basename(path).split('.')[0],
    readFileSync(path, 'utf-8')
  );
}

export async function loadPromptUrl(
  registry: Registry,

  name: string,
  url: string
): Promise<Dotprompt> {
  const fetch = (await import('node-fetch')).default;
  const response = await fetch(url);
  const text = await response.text();
  return Dotprompt.parse(registry, name, text);
}
