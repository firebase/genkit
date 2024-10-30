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
import { arrayFormatter } from './array';
import { enumFormatter } from './enum';
import { jsonFormatter } from './json';
import { jsonlFormatter } from './jsonl';
import { textFormatter } from './text';
import { Formatter } from './types';

export function defineFormat(
  registry: Registry,
  options: { name: string } & Formatter['config'],
  handler: Formatter['handler']
) {
  const { name, ...config } = options;
  const formatter = { config, handler };
  registry.registerValue('format', name, formatter);
  return formatter;
}

export type FormatArgument =
  | keyof typeof DEFAULT_FORMATS
  | Formatter
  | Omit<string, keyof typeof DEFAULT_FORMATS>;

export async function resolveFormat(
  registry: Registry,
  arg: FormatArgument
): Promise<Formatter | undefined> {
  if (typeof arg === 'string') {
    return registry.lookupValue<Formatter>('format', arg);
  }
  return arg as Formatter;
}

export const DEFAULT_FORMATS: Formatter<any, any>[] = [
  jsonFormatter,
  arrayFormatter,
  textFormatter,
  enumFormatter,
  jsonlFormatter,
];

/**
 * initializeFormats registers the default built-in formats on a registry.
 */
export function initializeFormats(registry: Registry) {
  for (const format of DEFAULT_FORMATS) {
    defineFormat(
      registry,
      { name: format.name, ...format.config },
      format.handler
    );
  }
}
