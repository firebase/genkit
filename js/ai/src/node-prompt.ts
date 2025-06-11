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

import { lazy } from '@genkit-ai/core/async';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import { existsSync, readdirSync, readFileSync } from 'fs';
import { basename, join, resolve } from 'path';
import {
  definePartial,
  definePromptAsync,
  PromptLoader,
  registryDefinitionKey,
} from './prompt';

export class NodePromptLoader implements PromptLoader {
  loadPromptFolder(registry: Registry, dir = './prompts', ns: string): void {
    const promptsPath = resolve(dir);
    if (existsSync(promptsPath)) {
      loadPromptFolderRecursively(registry, dir, ns, '');
    }
  }
}

function loadPromptFolderRecursively(
  registry: Registry,
  dir: string,
  ns: string,
  subDir: string
): void {
  const promptsPath = resolve(dir);
  const dirEnts = readdirSync(join(promptsPath, subDir), {
    withFileTypes: true,
  });
  for (const dirEnt of dirEnts) {
    const parentPath = join(promptsPath, subDir);
    const fileName = dirEnt.name;
    if (dirEnt.isFile() && fileName.endsWith('.prompt')) {
      if (fileName.startsWith('_')) {
        const partialName = fileName.substring(1, fileName.length - 7);
        definePartial(
          registry,
          partialName,
          readFileSync(join(parentPath, fileName), {
            encoding: 'utf8',
          })
        );
        logger.debug(
          `Registered Dotprompt partial "${partialName}" from "${join(parentPath, fileName)}"`
        );
      } else {
        // If this prompt is in a subdirectory, we need to include that
        // in the namespace to prevent naming conflicts.
        loadPrompt(
          registry,
          promptsPath,
          fileName,
          subDir ? `${subDir}/` : '',
          ns
        );
      }
    } else if (dirEnt.isDirectory()) {
      loadPromptFolderRecursively(registry, dir, ns, join(subDir, fileName));
    }
  }
}

function loadPrompt(
  registry: Registry,
  path: string,
  filename: string,
  prefix = '',
  ns = 'dotprompt'
): void {
  let name = `${prefix ?? ''}${basename(filename, '.prompt')}`;
  let variant: string | null = null;
  if (name.includes('.')) {
    const parts = name.split('.');
    name = parts[0];
    variant = parts[1];
  }
  const source = readFileSync(join(path, prefix ?? '', filename), 'utf8');
  const parsedPrompt = registry.dotprompt.parse(source);
  definePromptAsync(
    registry,
    registryDefinitionKey(name, variant ?? undefined, ns),
    // We use a lazy promise here because we only want prompt loaded when it's first used.
    // This is important because otherwise the loading may happen before the user has configured
    // all the schemas, etc., which will result in dotprompt.renderMetadata errors.
    lazy(async () => {
      const promptMetadata =
        await registry.dotprompt.renderMetadata(parsedPrompt);
      if (variant) {
        promptMetadata.variant = variant;
      }

      // dotprompt can set null description on the schema, which can confuse downstream schema consumers
      if (promptMetadata.output?.schema?.description === null) {
        delete promptMetadata.output.schema.description;
      }
      if (promptMetadata.input?.schema?.description === null) {
        delete promptMetadata.input.schema.description;
      }

      return {
        name: registryDefinitionKey(name, variant ?? undefined, ns),
        model: promptMetadata.model,
        config: promptMetadata.config,
        tools: promptMetadata.tools,
        description: promptMetadata.description,
        output: {
          jsonSchema: promptMetadata.output?.schema,
          format: promptMetadata.output?.format,
        },
        input: {
          jsonSchema: promptMetadata.input?.schema,
        },
        metadata: {
          ...promptMetadata.metadata,
          type: 'prompt',
          prompt: {
            ...promptMetadata,
            template: parsedPrompt.template,
          },
        },
        maxTurns: promptMetadata.raw?.['maxTurns'],
        toolChoice: promptMetadata.raw?.['toolChoice'],
        returnToolRequests: promptMetadata.raw?.['returnToolRequests'],
        messages: parsedPrompt.template,
      };
    })
  );
}
