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

import { PromptAction } from '@genkit-ai/ai';
import { GenkitError } from '@genkit-ai/core';
import { lookupAction } from '@genkit-ai/core/registry';
import { existsSync, readdir, readFileSync } from 'fs';
import { basename, join, resolve } from 'path';
import { Dotprompt } from './prompt.js';

export function registryDefinitionKey(name: string, variant?: string) {
  return `dotprompt/${name}${variant ? `.${variant}` : ''}`;
}

export function registryLookupKey(name: string, variant?: string) {
  return `/prompt/${registryDefinitionKey(name, variant)}`;
}

export async function lookupPrompt(
  name: string,
  variant?: string,
  dir: string = './prompts'
): Promise<Dotprompt> {
  // Expect to find the prompt in the registry
  const registryPrompt = (await lookupAction(
    registryLookupKey(name, variant)
  )) as PromptAction;
  if (registryPrompt) {
    return Dotprompt.fromAction(registryPrompt);
  } else {
    // Handle the case where initialization isn't complete
    // or a file was added after the prompt folder was loaded.
    return maybeLoadPrompt(dir, name, variant);
  }
}

async function maybeLoadPrompt(
  dir: string,
  name: string,
  variant?: string
): Promise<Dotprompt> {
  const expectedFileName = `${name}${variant ? `.${variant}` : ''}.prompt`;
  const promptFolder = resolve(dir);
  const promptExists = existsSync(join(promptFolder, expectedFileName));
  if (promptExists) {
    return loadPrompt(promptFolder, expectedFileName);
  } else {
    throw new GenkitError({
      source: 'dotprompt',
      status: 'NOT_FOUND',
      message: `Could not find '${expectedFileName}' in the prompts folder.`,
    });
  }
}

export async function loadPromptFolder(
  dir: string = './prompts'
): Promise<void> {
  const promptsPath = resolve(dir);
  return new Promise<void>((resolve, reject) => {
    if (existsSync(promptsPath)) {
      readdir(
        promptsPath,
        {
          withFileTypes: true,
          recursive: false,
        },
        (err, dirEnts) => {
          if (err) {
            reject(err);
          } else {
            dirEnts.forEach(async (dirEnt) => {
              if (dirEnt.isFile() && dirEnt.name.endsWith('.prompt')) {
                loadPrompt(dirEnt.path, dirEnt.name);
              }
            });
            resolve();
          }
        }
      );
    } else {
      resolve();
    }
  });
}

export function loadPrompt(path: string, filename: string): Dotprompt {
  let name = basename(filename, '.prompt');
  let variant: string | null = null;
  if (name.includes('.')) {
    const parts = name.split('.');
    name = parts[0];
    variant = parts[1];
  }
  const source = readFileSync(join(path, filename), 'utf8');
  const prompt = Dotprompt.parse(name, source);
  if (variant) {
    prompt.variant = variant;
  }
  prompt.define();
  return prompt;
}
