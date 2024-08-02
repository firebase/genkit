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

import {
  genkitPlugin,
  InitializedPlugin,
  PluginProvider,
} from '@genkit-ai/core';

import { readFileSync } from 'fs';
import { basename } from 'path';
import { defineDotprompt, Dotprompt, DotpromptRef } from './prompt.js';
import { loadPromptFolder, lookupPrompt } from './registry.js';

export { defineHelper, definePartial } from './template.js';
export { defineDotprompt, Dotprompt };

export interface DotpromptPluginOptions {
  // Directory to look for .prompt files.
  //
  // Note: This directory will be searched recursively, and any sub-directory
  // paths will be included in the prompt name. E.g. - if a prompt file is
  // located at `<dir>/foo/bar.prompt`, the prompt name will be `foo-bar`.
  dir: string;
}

export function dotprompt(
  params: DotpromptPluginOptions = { dir: './prompts' }
): PluginProvider {
  const plugin = genkitPlugin(
    'dotprompt',
    async (options: DotpromptPluginOptions): Promise<InitializedPlugin> => {
      await loadPromptFolder(options.dir);
      return {};
    }
  );
  return plugin(params);
}

export async function prompt<Variables = unknown>(
  name: string,
  options?: { variant?: string }
): Promise<Dotprompt<Variables>> {
  return (await lookupPrompt(name, options?.variant)) as Dotprompt<Variables>;
}

export function promptRef<Variables = unknown>(
  name: string,
  options?: { variant?: string; dir?: string }
): DotpromptRef<Variables> {
  return new DotpromptRef(name, options);
}

export function loadPromptFile(path: string): Dotprompt {
  return Dotprompt.parse(
    basename(path).split('.')[0],
    readFileSync(path, 'utf-8')
  );
}

export async function loadPromptUrl(
  name: string,
  url: string
): Promise<Dotprompt> {
  const fetch = (await import('node-fetch')).default;
  const response = await fetch(url);
  const text = await response.text();
  return Dotprompt.parse(name, text);
}
