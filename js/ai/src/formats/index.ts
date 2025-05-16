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

import { JSONSchema } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import { OutputOptions } from '../generate.js';
import { MessageData, TextPart } from '../model.js';
import { arrayFormatter } from './array.js';
import { enumFormatter } from './enum.js';
import { jsonFormatter } from './json.js';
import { jsonlFormatter } from './jsonl.js';
import { textFormatter } from './text.js';
import { type Formatter } from './types.js';

export { type Formatter };

export function defineFormat(
  registry: Registry,
  options: { name: string } & Formatter['config'],
  handler: Formatter['handler']
): { config: Formatter['config']; handler: Formatter['handler'] } {
  const { name, ...config } = options;
  const formatter = { config, handler };
  registry.registerValue('format', name, formatter);
  return formatter;
}

export type FormatArgument =
  | keyof typeof DEFAULT_FORMATS
  | Omit<string, keyof typeof DEFAULT_FORMATS>
  | undefined
  | null;

export async function resolveFormat(
  registry: Registry,
  outputOpts: OutputOptions | undefined
): Promise<Formatter<any, any> | undefined> {
  if (!outputOpts) return undefined;
  // If schema is set but no explicit format is set we default to json.
  if ((outputOpts.jsonSchema || outputOpts.schema) && !outputOpts.format) {
    return registry.lookupValue<Formatter>('format', 'json');
  }
  if (outputOpts.format) {
    return registry.lookupValue<Formatter>('format', outputOpts.format);
  }
  return undefined;
}

export function resolveInstructions(
  format?: Formatter,
  schema?: JSONSchema,
  instructionsOption?: boolean | string
): string | undefined {
  if (typeof instructionsOption === 'string') return instructionsOption; // user provided instructions
  if (instructionsOption === false) return undefined; // user says no instructions
  if (!format) return undefined;
  return format.handler(schema).instructions;
}

export function injectInstructions(
  messages: MessageData[],
  instructions: string | false | undefined
): MessageData[] {
  if (!instructions) return messages;

  // bail out if a non-pending output part is already present
  if (
    messages.find((m) =>
      m.content.find(
        (p) => p.metadata?.purpose === 'output' && !p.metadata?.pending
      )
    )
  ) {
    return messages;
  }

  const newPart: TextPart = {
    text: instructions,
    metadata: { purpose: 'output' },
  };

  // find the system message or the last user message
  let targetIndex = messages.findIndex((m) => m.role === 'system');
  if (targetIndex < 0)
    targetIndex = messages.map((m) => m.role).lastIndexOf('user');
  if (targetIndex < 0) return messages;

  const m = {
    ...messages[targetIndex],
    content: [...messages[targetIndex].content],
  };

  const partIndex = m.content.findIndex(
    (p) => p.metadata?.purpose === 'output' && p.metadata?.pending
  );
  if (partIndex > 0) {
    m.content.splice(partIndex, 1, newPart);
  } else {
    m.content.push(newPart);
  }

  const outMessages = [...messages];
  outMessages.splice(targetIndex, 1, m);
  return outMessages;
}

export const DEFAULT_FORMATS: Formatter<any, any>[] = [
  jsonFormatter,
  arrayFormatter,
  textFormatter,
  enumFormatter,
  jsonlFormatter,
];

/**
 * configureFormats registers the default built-in formats on a registry.
 */
export function configureFormats(registry: Registry) {
  for (const format of DEFAULT_FORMATS) {
    defineFormat(
      registry,
      { name: format.name, ...format.config },
      format.handler
    );
  }
}
