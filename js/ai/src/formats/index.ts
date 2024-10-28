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
import { arrayParser } from './array';
import { enumParser } from './enum';
import { jsonParser } from './json';
import { jsonlParser } from './jsonl';
import { textParser } from './text';
import { Formatter } from './types';

export const DEFAULT_FORMATS = {
  json: jsonParser,
  array: arrayParser,
  text: textParser,
  enum: enumParser,
  jsonl: jsonlParser,
};

export function defineFormat(
  registry: Registry,
  name: string,
  formatter: Formatter
) {
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
