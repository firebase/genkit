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
}

export type FormatArgument = string | Formatter;

export async function resolveFormat(
  registry: Registry,
  arg: FormatArgument
): Promise<Formatter | undefined> {
  if (typeof arg === 'string') {
    return registry.lookupValue<Formatter>('format', arg);
  }
  return arg;
}
